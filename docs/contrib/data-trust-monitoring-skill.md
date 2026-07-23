# Skill: Data-Trust Monitoring & Write-Back

> Draft for contribution to DataHub. A reusable convention + agent skill for
> autonomous data-quality agents that detect trust issues and record their
> findings back into DataHub as first-class metadata.
>
> **Target repo / format: confirm in the DataHub Community Slack
> `#agent-hackathon` before opening the PR** (candidates: the DataHub docs site,
> the skills registry, or `acryldata/mcp-server-datahub` examples).

## Motivation

Agents that operate on a data catalog produce findings (a stale table, a schema
drift, a dropped owner). Today those findings usually live in the agent's own
store and never make it back to the catalog, so the next human — or the next
agent — rediscovers them from scratch. DataHub already has the right primitives
to hold these findings; what's missing is a **convention** for how an automated
trust agent should write them, so results are consistent, queryable, and
non-destructive.

## The convention

When an agent detects a trust issue on an asset, write **two** artifacts:

### 1. A namespaced tag (fast, human-visible signal)

- Tag id/name: `trust:<issue_type>` — e.g. `trust:schema_drift`,
  `trust:freshness_stale`, `trust:owner_changed`, `trust:owner_missing`.
- Namespacing under a single `trust:` prefix keeps agent-authored tags easy to
  filter, bulk-review, and clean up, and prevents collisions with human tags.
- Shows on the asset page immediately; supports catalog-wide "show me everything
  the trust agent flagged" queries.

### 2. A custom assertion with a result (structured, auditable record)

- `upsertCustomAssertion(entityUrn, type=<issue_type>, description, fieldPath?)`
  to register/refresh the assertion.
- `reportAssertionResult(assertionUrn, type=FAILURE, severity=<LOW|MEDIUM|HIGH>)`
  to record the finding as a failing validation with a severity.
- Severity mapping from an agent's internal scale, e.g. `critical`/`high` → `HIGH`,
  `medium` → `MEDIUM`, `low` → `LOW`.
- Lives in the asset's Validation tab as a first-class, time-stamped record —
  the durable, auditable half of the signal.

### Principles

- **Additive, never destructive.** Only add tags/assertions; never edit owners,
  schemas, or descriptions authored by humans.
- **Idempotent.** Re-running detection updates the same assertion and re-uses the
  existing tag rather than duplicating.
- **Grounded provenance.** The assertion `description` should reference only facts
  the agent retrieved from DataHub (asset + lineage), not model-invented detail.

## Reference implementation

[Dataco](https://github.com/) implements this convention end-to-end:

- Detection: `check_asset(prev_state, current_meta)` over freshness / schema hash
  / ownership.
- Write-back: `tag_asset(urn, tag)` + `assert_issue(urn, issue_type, severity,
  description, field_path)` on a `DataHubGraph` handle
  (`create_tag` + `addTags`, then `upsert_custom_assertion` +
  `report_assertion_result`).
- Exposed over both an HTTP API and an MCP server so any agent can call it.

Minimal write-back (Python, `acryl-datahub`):

```python
from datahub.ingestion.graph.client import DataHubGraph, DatahubClientConfig

g = DataHubGraph(DatahubClientConfig(server=GMS_URL, token=TOKEN))

# 1. tag
tag_urn = g.create_tag("trust:schema_drift")          # idempotent-ish
g.execute_graphql(
    "mutation($t:String!,$r:String!){addTags(input:{tagUrns:[$t],resourceUrn:$r})}",
    variables={"t": tag_urn, "r": asset_urn},
)

# 2. assertion + failing result
res = g.upsert_custom_assertion(
    urn=None, entity_urn=asset_urn, type="schema_drift",
    description="Schema drift on patient_id (int -> str).", field_path="patient_id",
)
g.report_assertion_result(
    urn=res["urn"], timestamp_millis=now_ms, type="FAILURE", severity="HIGH",
)
```

## Open questions for the PR discussion

- Should `trust:` be a reserved/standard tag namespace, or a
  glossary-term-backed structured property?
- Preferred assertion `type` vocabulary for automated DQ agents.
- A recommended way to link the assertion back to the agent run / external URL.
