"""The scan agent — Dataco's autonomous loop against live DataHub.

For each monitored asset it: reads current metadata + lineage, compares against
the last-known ``MonitoringState`` to detect a trust issue, and when one fires it
creates the issue, produces a grounded explanation, and **writes the result back
into DataHub** (tag + assertion). This is the read → understand → act → write-back
loop Track 1 asks for.

Detection is deterministic and side-effect-isolated: no issue → the baseline is
simply refreshed; an issue → the full pipeline runs and the baseline advances so
a re-scan doesn't re-alert on the same change.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.domain.detection import check_asset
from app.domain.schema_diff import schema_hash
from app.domain.severity import compute_severity
from app.domain.types import IssueType, MonitoringState
from app.integrations.datahub import DataHubClient
from app.integrations.llm import LLMClient
from app.repository.models import IssueRecord, MonitoringStateModel
from app.repository.store import Repository
from app.services.reasoning import explain_issue
from app.services.writeback import write_back_issue


@dataclass
class ScanResult:
    urn: str
    detected: bool
    issue_id: str | None = None
    issue_type: str | None = None
    severity: str | None = None
    tag_urn: str | None = None
    assertion_urn: str | None = None
    detail: str = ""


def _naive(dt: datetime | None) -> datetime | None:
    """DataHub/SQLite round-trip timestamps as naive; keep comparisons naive."""
    if dt is not None and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _to_domain_state(model: MonitoringStateModel | None, urn: str) -> MonitoringState:
    if model is None:
        return MonitoringState(asset_id=urn)
    return MonitoringState(
        asset_id=urn,
        last_checked_at=_naive(model.last_checked_at),
        freshness_status=model.freshness_status,
        last_schema_hash=model.last_schema_hash or "",
        last_owner=model.last_owner,
        consecutive_failures=model.consecutive_failures or 0,
    )


def _stale_hours(prev: MonitoringState, now: datetime) -> float:
    if prev.last_checked_at is None:
        return 0.0
    return max(0.0, (now - prev.last_checked_at).total_seconds() / 3600)


def scan_asset(
    urn: str,
    *,
    datahub: DataHubClient,
    repo: Repository,
    llm: LLMClient,
    now: Callable[[], datetime] | None = None,
) -> ScanResult:
    now = now or datetime.now
    raw_now = now()
    current_time = raw_now.replace(tzinfo=None) if raw_now.tzinfo else raw_now

    meta = datahub.get_asset(urn)
    if meta is None:
        return ScanResult(urn=urn, detected=False, detail="asset not found")

    lineage = datahub.get_lineage(urn)
    prev = _to_domain_state(repo.get_monitoring_state(urn), urn)
    detection = check_asset(prev, meta, now=lambda: current_time)

    current_hash = schema_hash(meta.schema_fields) if meta.schema_fields else ""

    def _advance_baseline() -> None:
        repo.upsert_monitoring_state(
            MonitoringStateModel(
                asset_id=urn,
                last_schema_hash=current_hash,
                last_owner=meta.owner,
                last_checked_at=current_time,
            )
        )

    if detection is None:
        _advance_baseline()
        return ScanResult(urn=urn, detected=False, detail="no issue")

    issue_type: IssueType = detection["issue_type"]

    # Dedupe: if this asset already has an open issue of this type, don't create
    # a duplicate. Advance the baseline so the same drift stops re-alerting.
    existing = repo.find_active_issue(urn, issue_type.value)
    if existing is not None:
        _advance_baseline()
        # Self-heal: if a prior scan created the issue but died before writing
        # back (e.g. an LLM error), complete the write-back now.
        if existing.written_back_at is None:
            wb = write_back_issue(datahub, existing)
            repo.save_writeback(
                existing.id, tag_urn=wb.tag_urn, assertion_urn=wb.assertion_urn
            )
            return ScanResult(
                urn=urn,
                detected=False,
                issue_id=existing.id,
                issue_type=issue_type.value,
                tag_urn=wb.tag_urn,
                assertion_urn=wb.assertion_urn,
                detail="already tracked; wrote back",
            )
        return ScanResult(
            urn=urn,
            detected=False,
            issue_id=existing.id,
            issue_type=issue_type.value,
            detail="already tracked",
        )

    downstream = lineage.downstream
    blast_radius = len(downstream)
    stale = (
        _stale_hours(prev, current_time)
        if issue_type == IssueType.FRESHNESS_STALE
        else 0.0
    )
    severity = compute_severity(issue_type, blast_radius, stale)

    issue = IssueRecord(
        asset_id=urn,
        asset_name=meta.name,
        issue_type=issue_type.value,
        severity=severity.value,
        owner=meta.owner,
        blast_radius=blast_radius,
    )
    issue.set_impacted([n.name for n in downstream])
    repo.create_issue(issue)

    # Grounded explanation (persists summary/cause/confidence on the issue).
    explain_issue(issue, repo=repo, llm=llm, datahub=datahub)

    # Close the loop: push tag + assertion back into DataHub.
    wb = write_back_issue(datahub, issue)
    repo.save_writeback(
        issue.id, tag_urn=wb.tag_urn, assertion_urn=wb.assertion_urn
    )

    _advance_baseline()

    return ScanResult(
        urn=urn,
        detected=True,
        issue_id=issue.id,
        issue_type=issue_type.value,
        severity=severity.value,
        tag_urn=wb.tag_urn,
        assertion_urn=wb.assertion_urn,
        detail=wb.detail,
    )


def scan_all(
    urns: list[str],
    *,
    datahub: DataHubClient,
    repo: Repository,
    llm: LLMClient,
    now: Callable[[], datetime] | None = None,
) -> list[ScanResult]:
    return [
        scan_asset(urn, datahub=datahub, repo=repo, llm=llm, now=now)
        for urn in urns
    ]
