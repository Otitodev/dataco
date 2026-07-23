# Running Dataco

Practical runbook for the backend (FastAPI) and frontend (SvelteKit). Commands
are shown for **Windows PowerShell**; the equivalents work on macOS/Linux.

---

## 0. Python version — read this first

The project targets **Python 3.12** (`requires-python = ">=3.12"`). A `.venv`
lives in `backend/`. **Always use the venv's interpreter**, never a bare
`python`/`pip`.

> ⚠️ On this machine, bare `python` resolves to **Python 3.14**. Installing into
> 3.14 tries to **compile packages from Rust source** (no prebuilt wheels yet)
> and fails with `could not compile proc-macro2`. The 3.12 venv has wheels for
> everything — no compiler needed.

Two ways to target 3.12:

```powershell
# A) prefix every command with the venv interpreter (explicit, foolproof)
.\.venv\Scripts\python -m pytest

# B) activate once per terminal, then use plain python / pip / uvicorn
.\.venv\Scripts\Activate.ps1
python -m pytest
```

If the venv is missing, recreate it:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

---

## 1. Backend

### Install

```powershell
cd backend
.\.venv\Scripts\python -m pip install -e ".[dev]"        # app + dev tools
.\.venv\Scripts\python -m pip install -e ".[datahub]"    # optional: live DataHub client
```

### Seed the demo database

Creates `dataco.db` (SQLite) with the demo trust issues.

```powershell
.\.venv\Scripts\python seed.py
```

### Run the API

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --port 8000 --reload
```

- API base: `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- Interactive docs: `http://localhost:8000/docs`

CORS already allows the frontend dev server (`http://localhost:5173`).

### Tests & lint

```powershell
.\.venv\Scripts\python -m pytest           # full suite
.\.venv\Scripts\python -m ruff check .      # lint (see below)
```

---

## 2. Frontend

```powershell
cd frontend
npm install
npm run dev            # http://localhost:5173
```

The frontend calls the backend at `http://localhost:8000` by default
(override with `VITE_API_BASE`). Other useful scripts: `npm run check`
(type-check), `npm run build` (production build).

### Full end-to-end

Two terminals: run the seeded backend (`uvicorn ... --port 8000`) and the
frontend (`npm run dev`), then open `http://localhost:5173`. Dashboard →
click the critical issue → **Generate brief**.

---

## 3. Configuration (`.env`)

Copy `.env.example` to `.env` and fill in what you need. **Both the LLM and
DataHub layers fall back to offline stubs when no credentials are set**, so the
app runs end-to-end with zero secrets.

| Var | Values / example | Effect |
|---|---|---|
| `LLM_PROVIDER` | `anthropic` \| `openai` \| `stub` | Which LLM client to build |
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Unset → LLM falls back to the stub |
| `OPENAI_API_KEY` | `sk-...` | Unset → LLM falls back to the stub |
| `LLM_MODEL` | `claude-sonnet-5` | Optional; blank → provider default (`claude-opus-4-8` / `gpt-4o`) |
| `DATAHUB_PROVIDER` | `datahub` \| `fake` | Which DataHub client to build |
| `DATAHUB_URL` | `http://localhost:8080` | GMS **API** port (the UI is `9002`) |
| `DATAHUB_TOKEN` | a PAT | Unset → DataHub falls back to the seeded fake |

---

## 4. Live DataHub (optional)

Only needed to run `DataHubGraphClient` against real metadata. Requires **Docker
Desktop** and is resource-heavy (~8 GB RAM, ~13 GB disk).

```powershell
# acryl-datahub is installed via the .[datahub] extra above
.\.venv\Scripts\datahub docker quickstart          # boots the full stack
# → UI at http://localhost:9002   login: datahub / datahub

.\.venv\Scripts\datahub init --username datahub --password datahub
.\.venv\Scripts\datahub datapack load showcase-ecommerce   # ~1,050 demo entities
```

Then create a Personal Access Token in the UI (Settings → Access Tokens), set
`DATAHUB_TOKEN` and `DATAHUB_URL=http://localhost:8080` in `.env`, and restart
the API — the factory now builds the real client instead of the fake.

Manage the stack:

```powershell
.\.venv\Scripts\datahub docker quickstart --stop   # stop
.\.venv\Scripts\datahub docker nuke                # wipe everything
```

> The GraphQL queries in `DataHubGraphClient` use canonical field names but
> haven't been validated against a live instance yet — confirm lineage shape and
> wire dataset freshness (currently `None`) the first time you connect.

---

## 5. Common gotchas

- **`could not compile proc-macro2` / Rust errors on install** → you used
  Python 3.14. Use the 3.12 venv (§0).
- **Frontend shows "Can't reach the monitoring service"** → the backend isn't
  running on `:8000`, or it wasn't seeded.
- **Only `lab_ingestion_feed` opens; other issues 404** → the seeded fake
  DataHub only has that one asset. Expected until a live DataHub is connected.
- **`ruff check` reports findings** → pre-existing lint debt (unused imports,
  long lines); `ruff check --fix` clears the safe ones.
