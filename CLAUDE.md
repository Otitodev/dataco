# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Read `AGENTS.md` first.** It holds the authoritative operational runbook: exact venv/build/test commands, CI gates, offline-stub behaviour, and the live-DataHub gotchas. (The private infra runbook for the hosted instance — instance/SG IDs, SSH tunnel, restart steps — is in the gitignored `AGENTS.local.md`.) This file covers the code architecture that spans multiple files and isn't obvious from any single one. Don't duplicate what AGENTS.md already says.

## What this is

Dataco is a data-trust monitoring **agent** built for the DataHub "Agents That Do Real Work" hackathon (Track 1). It watches metadata assets, detects trust issues (staleness, schema drift, owner changes/loss), produces **grounded** LLM explanations and stakeholder briefs, and — the headline feature — **writes results back into DataHub** as a tag + a failing custom assertion, closing the read→detect→explain→act loop. Design is demo-first on purpose (seeded deterministic issues, offline stubs) — preserve the demo flow when changing things.

Two independent packages, **no root manifest** — run every command from inside the package dir.

- `backend/` — FastAPI + SQLAlchemy/SQLite, Python **3.12**. Entrypoint `app.main:app`. See `backend/RUN.md`.
- `frontend/` — SvelteKit 2 + Svelte 5 + Tailwind v4, Node 22. API client is `src/lib/api.ts`.

## Commands (see AGENTS.md for the full list and the venv caveat)

Bare `python` on this machine is 3.14 and breaks `pip install`. Always use the 3.12 venv:

```powershell
cd backend
.\.venv\Scripts\python seed.py                                    # (re)create dataco.db offline demo data
.\.venv\Scripts\python seed_live.py                               # prime monitoring baseline on real URNs (needs live DATAHUB_TOKEN)
.\.venv\Scripts\python -m uvicorn app.main:app --port 8000 --reload
.\.venv\Scripts\python -m app.mcp_server                          # MCP server over stdio (needs pip install -e ".[mcp]")
.\.venv\Scripts\python -m pytest                                  # full suite, fully offline
.\.venv\Scripts\python -m pytest tests/unit/test_severity.py::test_name   # single test
.\.venv\Scripts\python -m ruff check .                            # lint (88-col limit)
```

```bash
cd frontend && npm run dev      # dev server on :5173, talks to backend on :8000
npm run check                   # svelte-check (CI gate); npm run build is the other gate
```

CI (`.github/workflows/ci.yml`) installs `pip install -e ".[dev]"` — `anthropic`/`openai` are **core** deps, so they must stay importable; `acryl-datahub` is optional and its live-only tests `importorskip` it.

## Backend architecture: a layered, side-effect-free pipeline

The code is deliberately separated into layers so the domain logic stays pure and testable. Data flows inward from integrations → domain → repository, orchestrated by `app/services/`. **Two entrypoints — the FastAPI routers and the MCP server — are both thin wrappers over the service layer**; put logic in `app/services/`, not in either entrypoint.

- **`app/api/`** — FastAPI routers, one per resource (`dashboard`, `issues`, `assets`, `reasoning`, `scan`, `search`). Registered in `app/main.py`. Routers are thin: resolve DI, call a service, map records to `app/schemas/responses.py` Pydantic models by hand (no ORM-to-schema magic).
- **`app/services/`** — the shared, framework-free core called by both the API and the MCP server. `reasoning.py` (grounded `explain_issue`/`brief_issue`), `scan.py` (the agent loop), `writeback.py` (tag + assertion orchestration). This is where behaviour lives.
- **`app/domain/`** — pure functions and dataclasses (`types.py` holds the enums + dataclasses). `detection.py` decides issue type from previous vs. current `MonitoringState`/`AssetMeta`; `severity.py`, `confidence.py`, `blast_radius.py`, `schema_diff.py`, `grounding.py` are all deterministic and unit-tested in isolation. **No I/O, no DB, no network here** — keep it that way.
- **`app/integrations/`** — external boundaries behind `Protocol` interfaces: `DataHubClient` (`datahub.py`, read **and** write-back methods) and `LLMClient` (`llm.py`). Each `create_*_client()` factory **falls back to a deterministic stub/fake when the relevant credential env var is unset**, so the whole app runs offline with zero secrets. Provider SDKs (`anthropic`, `openai`, `acryl-datahub`) are imported lazily inside their branch — importing the module never requires the SDK. The live client is `datahub_graph.py`.
- **`app/repository/`** — `models.py` (SQLAlchemy ORM: `IssueRecord`, `BriefRecord`, `IssueNoteRecord`, `MonitoringStateModel`) and `store.py` (`Repository`, the only place that touches the session). `IssueRecord` carries write-back provenance (`datahub_tag_urn`/`datahub_assertion_urn`/`written_back_at`). Issues sort by a `SEVERITY_ORDER` case expression, not alphabetically.
- **`app/deps.py`** — DI providers (`get_repo`, `get_datahub`, `get_llm`, `get_db`). Clients are module-level singletons settable via `set_*_client`; tests swap them through `app.dependency_overrides` (see `tests/conftest.py`).
- **`app/mcp_server.py`** — a FastMCP server exposing the same capabilities as tools (`list_issues`, `search_assets`, `scan_asset_tool`, `explain_issue_tool`, `generate_brief_tool`, `annotate_datahub`), each reusing the service layer. Optional `.[mcp]` extra.

### The grounded reasoning flow (the core feature)

`app/services/reasoning.py` is where the anti-hallucination design lives — study it before touching LLM behaviour. The API router (`app/api/reasoning.py`), the scan agent, and the MCP server all call these functions, so the invariants hold everywhere:

1. `build_context()` assembles a bundle strictly from DataHub (asset metadata + upstream/downstream lineage). The LLM only ever sees retrieved facts.
2. `llm.explain(context)` / `llm.brief(context)` return structured objects. A **runtime** LLM failure (e.g. invalid/expired key → 401) is caught and falls back to the deterministic stub, so a scan never 500s on a bad key.
3. **Grounding guard**: `ground_assets()` strips any asset the model named that isn't in `allowed_assets(context)` (the affected asset + its lineage). The model cannot introduce assets that weren't retrieved.
4. **Confidence is rule-based**, computed by `confidence_label()` from context completeness (owner present? lineage complete?) — *not* the model's self-report.
5. The result is persisted so explanations are durable and set the issue's confidence/blast-radius.

When adding LLM capabilities, preserve steps 3–4: never trust model-supplied asset names or confidence.

### The scan agent + write-back (the Track-1 "does real work" loop)

`POST /scan` → `app/services/scan.py` `scan_asset(urn)`:

1. Read live DataHub (`get_asset` + `get_lineage`).
2. `detection.check_asset(prev_state, meta)` vs. the stored `MonitoringState` — no change → refresh baseline and return.
3. On a hit: create the `IssueRecord`, run the grounded explanation, then **write back to DataHub** (`app/services/writeback.py`): a namespaced tag (`DATAHUB_TAG_PREFIX:issue_type`, default `trust:`) + a custom assertion with a FAILURE result, via `DataHubGraphClient.tag_asset`/`assert_issue`. Provenance is saved on the issue.
4. Advance the monitoring baseline so a re-scan doesn't re-alert.

Idempotency + resilience baked in: the assertion URN is deterministic (`_assertion_id`, sha1 of asset+issue_type) so re-writes upsert one assertion instead of duplicating; dedupe is **self-healing** — an existing active issue that was never written back gets its write-back completed on the next scan. Watchlist of real URNs is `app/monitored_assets.py`; `seed_live.py` primes deterministic baselines against a live instance. Write-back is gated by `DATAHUB_WRITE_ENABLED` (default on) and the `FakeDataHubClient` records writes to `.writes` so the offline path stays demonstrable.

## Cross-cutting gotchas

- **App code imports from `tests/` at runtime.** The stub fallbacks do `from tests.fakes import ...` and `seed.py`/`seed_live.py` import `tests.factories`. `tests/` is on the runtime path — don't move, rename, or "clean up" `tests/fakes.py` / `tests/factories.py`.
- **Env loading is manual.** `app/config.py` reads env via `os.getenv` at import time; nothing auto-loads `backend/.env`. Pass `--env-file .env` to uvicorn or export vars. `DATAHUB_URL` is the GMS API port (8080), not the UI (9002). Gotcha: an inline comment on an *empty* `.env` value (`LLM_MODEL=   # note`) is mis-parsed by python-dotenv as the value itself — `config._clean()` guards the provider/model fields; keep comments on their own line.
- **Provider is config-only.** Switch LLMs with `LLM_PROVIDER` (`anthropic`|`openai`|`stub`) + the matching key + optional `OPENAI_MODEL`/`LLM_MODEL`. Switch DataHub source with `DATAHUB_PROVIDER`/`DATAHUB_TOKEN`.
- **Test layers** mirror the architecture: `tests/unit` (pure domain), `tests/api` (TestClient), `tests/integration` (repository against temp-file SQLite). Fully offline. `datahub_graph.py` must stay SDK-free at import *and* at call time on the read/degradation path (`_is_not_found` matches `GraphError` by class name) so the offline mapping tests run without `acryl-datahub`.
- The seeded fake DataHub only contains the `lab_ingestion_feed` asset, and the seeded `urn:dataco:*` issues resolve only against the fake — other detail pages 404 until a live DataHub is connected. For a live end-to-end demo use `seed_live.py` + `/scan` (real URNs), not `seed.py`. Expected, not a bug.

## Frontend conventions

- Single API client `src/lib/api.ts` (base URL `VITE_API_BASE`, default `http://localhost:8000`); its TypeScript interfaces mirror the backend response schemas. CORS on the backend already allows `:5173`/`:4173`.
- Design system is in `frontend/DESIGN.md`, enforced via Tailwind v4 `@theme` tokens in `src/app.css`: use tokens (`bg-brand`, `text-ink-600`, `bg-severity-critical`…), **never hardcode hex**. Colour appears only where it means something (severity). Light mode only. Matches the user's Apple-minimal design preference.
