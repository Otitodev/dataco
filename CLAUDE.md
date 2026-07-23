# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Read `AGENTS.md` first.** It holds the authoritative operational runbook: exact venv/build/test commands, CI gates, the offline-stub behaviour, and the live-DataHub-on-EC2 workflow. This file covers the code architecture that spans multiple files and isn't obvious from any single one. Don't duplicate what AGENTS.md already says.

## What this is

Dataco is a data-trust monitoring tool built for a DataHub hackathon. It watches metadata assets, detects trust issues (staleness, schema drift, owner changes/loss), and produces **grounded** LLM explanations and stakeholder briefs. Design is demo-first on purpose (seeded deterministic issues, offline stubs) — preserve the demo flow when changing things.

Two independent packages, **no root manifest** — run every command from inside the package dir.

- `backend/` — FastAPI + SQLAlchemy/SQLite, Python **3.12**. Entrypoint `app.main:app`. See `backend/RUN.md`.
- `frontend/` — SvelteKit 2 + Svelte 5 + Tailwind v4, Node 22. API client is `src/lib/api.ts`.

## Commands (see AGENTS.md for the full list and the venv caveat)

Bare `python` on this machine is 3.14 and breaks `pip install`. Always use the 3.12 venv:

```powershell
cd backend
.\.venv\Scripts\python seed.py                                    # (re)create dataco.db demo data
.\.venv\Scripts\python -m uvicorn app.main:app --port 8000 --reload
.\.venv\Scripts\python -m pytest                                  # full suite, fully offline
.\.venv\Scripts\python -m pytest tests/unit/test_severity.py::test_name   # single test
.\.venv\Scripts\python -m ruff check .                            # lint (88-col limit)
```

```bash
cd frontend && npm run dev      # dev server on :5173, talks to backend on :8000
npm run check                   # svelte-check (CI gate); npm run build is the other gate
```

## Backend architecture: a layered, side-effect-free pipeline

The code is deliberately separated into layers so the domain logic stays pure and testable. Data flows inward from integrations → domain → repository, wired by FastAPI DI.

- **`app/api/`** — FastAPI routers, one per resource (`dashboard`, `issues`, `assets`, `reasoning`, `search`). Registered in `app/main.py`. Routers are thin: they resolve dependencies, call domain/integration code, and map records to `app/schemas/responses.py` Pydantic models by hand (no ORM-to-schema magic).
- **`app/domain/`** — pure functions and dataclasses (`types.py` holds the enums + dataclasses). `detection.py` decides issue type from previous vs. current `MonitoringState`/`AssetMeta`; `severity.py`, `confidence.py`, `blast_radius.py`, `schema_diff.py`, `grounding.py` are all deterministic and unit-tested in isolation. **No I/O, no DB, no network here** — keep it that way.
- **`app/integrations/`** — external boundaries behind `Protocol` interfaces: `DataHubClient` (`datahub.py`) and `LLMClient` (`llm.py`). Each has a `create_*_client()` factory that **falls back to a deterministic stub/fake when the relevant credential env var is unset**, so the whole app runs offline with zero secrets. Provider SDKs (`anthropic`, `openai`, `acryl-datahub`) are imported lazily inside their branch — importing the module never requires the SDK.
- **`app/repository/`** — `models.py` (SQLAlchemy ORM: `IssueRecord`, `BriefRecord`, `IssueNoteRecord`, `MonitoringStateModel`) and `store.py` (`Repository`, the only place that touches the session). Issues sort by a `SEVERITY_ORDER` case expression, not alphabetically.
- **`app/deps.py`** — DI providers (`get_repo`, `get_datahub`, `get_llm`, `get_db`). Clients are module-level singletons settable via `set_*_client`; tests swap them through `app.dependency_overrides` (see `tests/conftest.py`).

### The grounded reasoning flow (the core feature)

`app/api/reasoning.py` is where the anti-hallucination design lives — study it before touching LLM behaviour:

1. `_build_context()` assembles a bundle strictly from DataHub (asset metadata + upstream/downstream lineage). The LLM only ever sees retrieved facts.
2. `llm.explain(context)` / `llm.brief(context)` return structured objects.
3. **Grounding guard**: `ground_assets()` strips any asset the model named that isn't in `_allowed_assets(context)` (the affected asset + its lineage). The model cannot introduce assets that weren't retrieved.
4. **Confidence is rule-based**, computed by `confidence_label()` from context completeness (owner present? lineage complete?) — *not* the model's self-report.
5. The result is persisted so explanations are durable and set the issue's confidence/blast-radius.

When adding LLM capabilities, preserve steps 3–4: never trust model-supplied asset names or confidence.

## Cross-cutting gotchas

- **App code imports from `tests/` at runtime.** The stub fallbacks do `from tests.fakes import ...` and `seed.py` imports `tests.factories`. `tests/` is on the runtime path — don't move, rename, or "clean up" `tests/fakes.py` / `tests/factories.py`.
- **Env loading is manual.** `app/config.py` reads env via `os.getenv` at import time; nothing auto-loads `backend/.env`. Pass `--env-file .env` to uvicorn or export vars. `DATAHUB_URL` is the GMS API port (8080), not the UI (9002).
- **Test layers** mirror the architecture: `tests/unit` (pure domain), `tests/api` (TestClient), `tests/integration` (repository against temp-file SQLite). No external services are ever needed to run tests.
- The seeded fake DataHub only contains the `lab_ingestion_feed` asset — other issue detail pages 404 until a live DataHub is connected. Expected, not a bug.

## Frontend conventions

- Single API client `src/lib/api.ts` (base URL `VITE_API_BASE`, default `http://localhost:8000`); its TypeScript interfaces mirror the backend response schemas. CORS on the backend already allows `:5173`/`:4173`.
- Design system is in `frontend/DESIGN.md`, enforced via Tailwind v4 `@theme` tokens in `src/app.css`: use tokens (`bg-brand`, `text-ink-600`, `bg-severity-critical`…), **never hardcode hex**. Colour appears only where it means something (severity). Light mode only. Matches the user's Apple-minimal design preference.
