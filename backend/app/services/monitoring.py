"""Manage the set of assets Dataco watches — the onboarding surface.

Adding an asset primes a ``MonitoringState`` baseline at the asset's **current**
state, so the agent starts watching for *future* drift without firing a false
alert on day one. Removing an asset drops that baseline. Because the scan
watchlist is resolved from these rows (``scan.resolve_urns`` →
``repo.list_monitored_urns``), adding here immediately puts an asset in the loop.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.domain.schema_diff import schema_hash
from app.integrations.datahub import DataHubClient
from app.repository.models import MonitoringStateModel
from app.repository.store import Repository


@dataclass
class MonitoredAsset:
    urn: str
    name: str
    owner: str | None
    last_checked_at: datetime | None
    active_issue: bool


def _short_name(urn: str) -> str:
    """A readable fallback name when DataHub can't resolve the asset."""
    seg = urn.rsplit(",", 1)[-1].rstrip(")")
    seg = seg.rsplit(":", 1)[-1]
    return seg.rsplit(".", 1)[-1] if "@" not in seg else seg


def add_monitored_asset(
    urn: str,
    *,
    datahub: DataHubClient,
    repo: Repository,
    now: Callable[[], datetime] | None = None,
) -> MonitoredAsset | None:
    """Start watching ``urn``. Returns None if DataHub doesn't know the asset."""
    meta = datahub.get_asset(urn)
    if meta is None:
        return None
    now = now or datetime.now
    current = now()
    if current.tzinfo is not None:
        current = current.replace(tzinfo=None)
    # Baseline = current state, so future changes are what get detected.
    current_hash = schema_hash(meta.schema_fields) if meta.schema_fields else ""
    repo.upsert_monitoring_state(
        MonitoringStateModel(
            asset_id=urn,
            last_schema_hash=current_hash,
            last_owner=meta.owner,
            last_checked_at=current,
        )
    )
    return MonitoredAsset(
        urn=urn,
        name=meta.name,
        owner=meta.owner,
        last_checked_at=current,
        active_issue=False,
    )


def list_monitored_assets(
    *, datahub: DataHubClient, repo: Repository
) -> list[MonitoredAsset]:
    active_ids = {i.asset_id for i in repo.list_active_issues()}
    states = repo.list_monitoring_states()
    # One DataHub round-trip for all watched assets (not one call each).
    metas = datahub.get_assets([s.asset_id for s in states])
    assets: list[MonitoredAsset] = []
    for state in states:
        meta = metas.get(state.asset_id)
        assets.append(
            MonitoredAsset(
                urn=state.asset_id,
                name=meta.name if meta else _short_name(state.asset_id),
                owner=meta.owner if meta else state.last_owner,
                last_checked_at=state.last_checked_at,
                active_issue=state.asset_id in active_ids,
            )
        )
    return assets


def remove_monitored_asset(urn: str, *, repo: Repository) -> bool:
    return repo.delete_monitoring_state(urn)
