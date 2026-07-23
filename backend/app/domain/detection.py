from collections.abc import Callable
from datetime import datetime, timedelta

from app.domain.schema_diff import schema_hash
from app.domain.types import AssetMeta, IssueType, MonitoringState


def check_asset(
    prev_state: MonitoringState,
    current_meta: AssetMeta,
    now: Callable[[], datetime] | None = None,
) -> dict | None:
    if now is None:
        now = datetime.now

    current_time = now()
    issue_type = None

    new_schema_hash = (
        schema_hash(current_meta.schema_fields)
        if current_meta.schema_fields
        else ""
    )

    if (
        prev_state.last_schema_hash
        and new_schema_hash
        and prev_state.last_schema_hash != new_schema_hash
    ):
        issue_type = IssueType.SCHEMA_DRIFT
    elif (
        prev_state.last_owner
        and current_meta.owner
        and prev_state.last_owner != current_meta.owner
    ):
        issue_type = IssueType.OWNER_CHANGED
    elif prev_state.last_owner and current_meta.owner is None:
        issue_type = IssueType.OWNER_MISSING
    elif (
        prev_state.last_checked_at
        and current_time > prev_state.last_checked_at + timedelta(hours=24)
    ):
        issue_type = IssueType.FRESHNESS_STALE

    if issue_type is None:
        return None

    return {
        "issue_type": issue_type,
        "new_schema_hash": new_schema_hash,
        "current_owner": current_meta.owner,
    }
