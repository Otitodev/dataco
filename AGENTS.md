# AGENTS.md

Dataco: data-trust monitoring tool, built for **Build with DataHub: The Agent Hackathon** (DataHub, Jul 6 – Aug 10 2026, datahub.devpost.com) — fits the "Agents that do real work" category. Design choices are demo-first on purpose (seeded deterministic issues, offline stubs, copyable briefs) — preserve the demo flow when changing things.

Two independent packages, **no root manifest** — run every command from inside the package dir.

- `backend/` — FastAPI + SQLAlchemy/SQLite, Python **3.12**. Entrypoint `app.main:app`. `backend/RUN.md` is the authoritative runbook.
- `frontend/` — SvelteKit 2 + Svelte 5 + Tailwind v4, Node 22. API client is `src/lib/api.ts`.
- `docs/` — PRD/TRD/MVP/implementation plan (prose; trust code over docs on conflict).

## Backend: use the venv, never bare `python`

Bare `python` on this machine is **3.14** — `pip install` there fails compiling from Rust (`could not compile proc-macro2`). Always prefix with the 3.12 venv in `backend/`:

```powershell
cd backend
.\.venv\Scripts\python -m pip install -e ".[dev]"   # install
.\.venv\Scripts\python seed.py                       # create dataco.db offline demo data (gitignored)
.\.venv\Scripts\python seed_live.py                  # prime monitoring baseline on real URNs (needs live token)
.\.venv\Scripts\python -m uvicorn app.main:app --port 8000 --reload
.\.venv\Scripts\python -m app.mcp_server             # MCP server over stdio (needs pip install -e ".[mcp]")
.\.venv\Scripts\python -m pytest                     # full suite (~97 tests, fully offline)
.\.venv\Scripts\python -m pytest tests/unit/test_severity.py::test_name   # single test
.\.venv\Scripts\python -m ruff check .               # lint — see note below
```

## Verification & CI (`.github/workflows/ci.yml`)

- CI gates: backend `ruff check .` + `pytest -q` (py3.12); frontend `npx svelte-check` + `npm run build` (Node 22). Frontend equivalent of the check is `npm run check`.
- `ruff check .` is green (E501/N806 debt cleared 2026-07-23) — keep new code within 88 cols; pytest remains the reliable local gate.
- `mypy` is a dev dep but has no config and is not CI-enforced.

## Non-obvious architecture facts

- **Offline by default**: `create_llm_client()` / `create_datahub_client()` in `app/integrations/` fall back to deterministic stubs when API key/token env vars are unset — app, seed, and tests all run with zero secrets. Additionally, `services/reasoning.py` catches *runtime* LLM failures (e.g. an invalid/expired key → 401) and falls back to the stub per-call, so a scan never 500s on a bad key.
- **App code imports from `tests/` at runtime**: the stub fallbacks do `from tests.fakes import ...` and `seed.py` imports `tests.factories`. `tests/` is on the runtime path — don't move, rename, or "clean up" those fakes/factories.
- **Env loading**: `app/config.py` reads process env via `os.getenv` at import time. Nothing auto-loads `backend/.env` — pass `--env-file .env` to uvicorn or export vars in the shell. `DATAHUB_URL` is the GMS **API** port (8080), not the UI (9002). **`.env` gotcha:** an inline comment on an *empty* value (`LLM_MODEL=   # note`) is mis-parsed by python-dotenv (uvicorn `--env-file`) as the value itself — which silently became the OpenAI model id (→ "invalid model ID"). `config._clean()` now strips whitespace and drops comment-like values for the provider/model fields; keep comments on their own line in `.env`. Switching LLM providers is config-only: `LLM_PROVIDER=openai` + `OPENAI_API_KEY` + `OPENAI_MODEL` (validated live with `gpt-5.6-luna`).
- **DI wiring**: providers in `app/deps.py`; tests override via `app.dependency_overrides` (see `tests/conftest.py`). Tests use temp-file SQLite — no external services needed. Test layers: `tests/unit` (domain), `tests/api` (TestClient), `tests/integration` (repository).
- **`app/services/` is the shared core**: `reasoning.py` (grounded explain/brief — extracted from the API so routes, the scan agent, and MCP all call it), `scan.py` (the agent loop), `writeback.py` (tag + assertion). API routers and `app/mcp_server.py` are thin wrappers over these; keep logic here, not in either entrypoint.
- **The scan agent** (`POST /scan` → `services/scan.py`): reads live DataHub, runs `detection.check_asset` vs the stored `MonitoringState`, and on a hit creates the issue, explains it, **writes a tag + assertion back to DataHub**, then advances the baseline so a re-scan doesn't re-alert. `seed_live.py` primes deterministic baselines on the `app/monitored_assets.py` watchlist (real `b2fd91.*` URNs); it self-loads `.env`. Dedupe is self-healing: if an active issue for the asset+type already exists, the scan skips creating a duplicate but still completes the write-back if that issue was never written back (`written_back_at is None`). The assertion URN is deterministic (`_assertion_id`, sha1 of asset+issue_type) so re-writes upsert one assertion in place instead of piling up duplicates. URN resolution (`services/scan.py` `resolve_urns`) is shared by the endpoint and the scheduler: explicit request → primed monitoring baseline → static `WATCHLIST`.
- **Continuous scanning (opt-in)** (`app/services/scheduler.py`, wired via `main.py` lifespan): set `SCAN_INTERVAL_SECONDS=N` (default `0` = off) to run the agent every N seconds with no human trigger — one run on startup, then on the interval. The loop runs outside the request cycle, so it opens its own `SessionLocal()` per cycle and calls the same `scan_all` path; each cycle is try/except-wrapped so a transient failure logs and the loop survives. `GET /scan/status` reports `enabled/interval_seconds/last_run_at/last_scanned/last_detected/watch_count` (dashboard shows an "Auto-scan" badge). **Default-off is deliberate**: `create_app()` runs per test fixture, so an always-on loop would spawn in every test. **`--workers N` caveat**: each worker starts its own loop (N concurrent scanners) — harmless because scans are idempotent (deterministic assertion URN + self-healing dedupe) but wasteful; the demo runs a single worker. Enable for the demo: `SCAN_INTERVAL_SECONDS=300 uvicorn app.main:app ...` (or in `.env`).
- **Write-back** (`app/integrations/datahub_graph.py` `tag_asset`/`assert_issue`): tags are namespaced `DATAHUB_TAG_PREFIX:issue_type` (default `trust:`); assertions use `upsert_custom_assertion` then report a FAILURE result. Gated by `DATAHUB_WRITE_ENABLED` (default on). The recording `FakeDataHubClient` logs writes to `.writes` so the offline path stays demonstrable. Provenance persists on `IssueRecord.datahub_tag_urn/datahub_assertion_urn/written_back_at`. **Validated live against quickstart v1.5.x — three server-compat gotchas were needed and are baked in:** (1) `upsert_custom_assertion` **requires `platform_name`** ("Platform Name or Platform Urn must be specified") — we pass `"dataco"`; (2) the SDK's `report_assertion_result` sends a `severity` field the older server's `AssertionResultInput` lacks (`Unknown type AssertionResultSeverity`), so we report via a hand-rolled `_REPORT_RESULT_MUTATION` that carries severity as a `properties` entry instead; (3) a freshly-upserted assertion is **eventually consistent** — reporting its result 500s with "does not exist" for a moment, so `assert_issue` retries the report a few times with a 2s backoff.
- **Live read paths degrade, not 500**: `DataHubGraphClient.get_asset/get_lineage/search` catch not-found `GraphError` and return `None`/empty (see `_run`); genuine errors re-raise. Tests for this live in `tests/unit/test_graph_degradation.py` and `importorskip` the SDK so CI (no `acryl-datahub`) skips them.
- Seeded fake DataHub only contains the `lab_ingestion_feed` asset — other issue detail pages 404 until a live DataHub is connected. Expected, not a bug. The seeded `urn:dataco:*` issues only resolve against the fake; for a live end-to-end demo use `seed_live.py` + `/scan` (real URNs), not `seed.py`.
## Live DataHub

For a live end-to-end demo, point the backend at any DataHub instance (e.g. `datahub docker quickstart`) by setting `DATAHUB_TOKEN` and `DATAHUB_URL` (the GMS API on `:8080`) in `backend/.env`, then `seed_live.py` → `POST /scan` (see `README.md`). `DataHubGraphClient` was validated against a `datahub docker quickstart` + showcase-ecommerce instance (CLI 1.6.x). Pack quirk: names/owners carry a `b2fd91.` namespace prefix, and freshly loaded metadata is eventually consistent — search/lineage can return empty for the first minutes after a load.

The operational runbook for this project's own hosted instance (cloud instance/security-group IDs, SSH-tunnel access, DataHub restart + disk-space steps, UI login) lives in **`AGENTS.local.md`**, which is **gitignored and not committed**.

## Frontend conventions

- Calls backend at `VITE_API_BASE` (default `http://localhost:8000`); CORS already allows `:5173`/`:4173`. Run backend seeded + `npm run dev` for the full demo.
- Design system is documented in `frontend/DESIGN.md` and enforced via tokens in `src/app.css` (Tailwind v4 `@theme`): use tokens (`bg-brand`, `text-ink-600`, `bg-severity-critical`…), never hardcode hex; **colour appears only where it means something** (severity); light mode only.
