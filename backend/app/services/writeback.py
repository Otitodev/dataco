"""Write detected issues back into DataHub — the step that turns Dataco from a
reader into an agent that *does real work* (Track 1: results go back to the
system for future reference).

For an issue we push two artifacts onto the affected asset:
  - a namespaced **tag** (e.g. ``trust:schema_drift``) — visible on the asset
    page, so a human browsing DataHub sees the trust signal immediately;
  - a custom **assertion** with a FAILURE result — a first-class DataHub
    validation record in the asset's Validation tab.

Both writes are best-effort and isolated: a failure on one is recorded in the
result but never raises, so a partial DataHub outage can't break a scan.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import DATAHUB_TAG_PREFIX, DATAHUB_WRITE_ENABLED
from app.integrations.datahub import DataHubClient


@dataclass
class WriteBackResult:
    ok: bool
    tag_urn: str | None = None
    assertion_urn: str | None = None
    detail: str = ""


def _tag_for(issue_type: str) -> str:
    return f"{DATAHUB_TAG_PREFIX}:{issue_type}"


def _description_for(issue) -> str:
    summary = (issue.summary or "").strip()
    base = f"Dataco detected {issue.issue_type} on {issue.asset_name} "
    base += f"(severity: {issue.severity})."
    return f"{base} {summary}".strip()


def write_back_issue(datahub: DataHubClient, issue) -> WriteBackResult:
    """Tag + assert the issue on its asset in DataHub. Never raises."""
    if not DATAHUB_WRITE_ENABLED:
        return WriteBackResult(ok=False, detail="write-back disabled")

    tag_urn = datahub.tag_asset(issue.asset_id, _tag_for(issue.issue_type))
    assertion_urn = datahub.assert_issue(
        issue.asset_id,
        issue_type=issue.issue_type,
        severity=issue.severity,
        description=_description_for(issue),
    )

    ok = bool(tag_urn or assertion_urn)
    detail = "wrote " + ", ".join(
        part
        for part, present in (("tag", tag_urn), ("assertion", assertion_urn))
        if present
    ) if ok else "no artifacts written"
    return WriteBackResult(
        ok=ok, tag_urn=tag_urn, assertion_urn=assertion_urn, detail=detail
    )
