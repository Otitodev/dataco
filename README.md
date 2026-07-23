# Dataco — a data-trust agent for DataHub

**Dataco watches your DataHub assets, detects trust issues, explains them with
context you can trust, and writes the result back into DataHub.** Built for
[Build with DataHub: The Agent Hackathon](https://datahub.com/blog/build-with-datahub-agent-hackathon/)
(Track 1 — *Agents That Do Real Work*).

Agents fail in production when they lack context about **ownership, lineage, and
governance**. Dataco treats DataHub as that context layer and closes the loop:

> **read** DataHub → **understand** the blast radius → **act** (grounded
> explanation) → **write results back** (tag + assertion on the asset).

## The loop

```
POST /scan
  1. read     get_asset(urn) + get_lineage(urn)          ← live DataHub
  2. detect   check_asset(prev_state, current_meta)       ← schema drift / owner / freshness
  3. explain  grounded LLM summary + likely cause         ← only cites retrieved assets
  4. write    tag  trust:schema_drift                     → back onto the asset
              assertion (FAILURE, severity HIGH)          → asset Validation tab
  5. advance  update the monitoring baseline
```

Every explanation is **grounded**: the model only ever sees facts retrieved from
DataHub, a guard strips any asset it names that wasn't retrieved, and confidence
is computed from how complete the context is — never the model's self-report.

See real outputs in [`examples/`](./examples/) and the write-back detail in
[`examples/datahub-writeback.md`](./examples/datahub-writeback.md).

## Interfaces

- **HTTP API** (FastAPI): `/scan`, `/dashboard`, `/explain`, `/brief`,
  `/issue/{id}/writeback`, `/search`, `/asset/{urn}`, `/lineage/{urn}`.
- **MCP server**: the same tools over the Model Context Protocol, so any MCP
  client (Claude Desktop, IDEs, other agents) can drive Dataco directly.
- **Web UI** (SvelteKit): dashboard → issue detail → explanation & copyable brief.

## Quickstart (offline — zero secrets)

Dataco runs fully offline: with no DataHub token or LLM key set, it falls back to
a seeded fake DataHub and a deterministic stub LLM. Python **3.12**, Node **22**.

```bash
# backend
cd backend
python -m venv .venv && .\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python seed.py                                  # demo issues
.\.venv\Scripts\python -m uvicorn app.main:app --port 8000      # http://localhost:8000/docs

# frontend (separate terminal)
cd frontend
npm install && npm run dev                                      # http://localhost:5173
```

## Live DataHub

Point Dataco at a real instance (`datahub docker quickstart`) by setting
`DATAHUB_TOKEN` (and `DATAHUB_URL`, the GMS API on `:8080`) in `backend/.env`,
then prime a baseline and run the agent:

```bash
cd backend
.\.venv\Scripts\python seed_live.py                             # baseline on real URNs
.\.venv\Scripts\python -m uvicorn app.main:app --port 8000 --env-file .env
curl -X POST http://localhost:8000/scan                         # detect + explain + write back
```

The detected issue's `trust:*` tag and FAILURE assertion then appear on the asset
in the DataHub UI. Write-back is controlled by `DATAHUB_WRITE_ENABLED` (default on)
and `DATAHUB_TAG_PREFIX` (default `trust`).

## MCP server

```bash
cd backend
.\.venv\Scripts\python -m pip install -e ".[mcp]"
.\.venv\Scripts\python -m app.mcp_server        # stdio
```

Example client config:

```json
{
  "mcpServers": {
    "dataco": {
      "command": "backend/.venv/Scripts/python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "backend"
    }
  }
}
```

Tools: `list_issues`, `search_assets`, `scan_asset_tool`, `explain_issue_tool`,
`generate_brief_tool`, `annotate_datahub`.

## Architecture

Layered, side-effect-free at the core; DataHub and the LLM sit behind `Protocol`
interfaces with offline-stub factories.

```
app/api/          thin FastAPI routers
app/services/     framework-free orchestration — reasoning, scan, writeback
                  (shared by the HTTP routes AND the MCP server)
app/domain/       pure functions: detection, severity, grounding, schema diff
app/integrations/ DataHubClient + LLMClient protocols and implementations
app/repository/   SQLAlchemy models + Repository (SQLite)
```

## Tests

```bash
cd backend
.\.venv\Scripts\python -m pytest        # fully offline, no secrets
.\.venv\Scripts\python -m ruff check .
```

## License

[Apache-2.0](./LICENSE).
