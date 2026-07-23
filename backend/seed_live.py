r"""Prime the monitoring baseline for LIVE DataHub assets so the scan agent
detects a real issue on its first run.

Unlike ``seed.py`` (which inserts fixed offline demo issues), this seeds only
``MonitoringState`` rows for real URNs from the connected DataHub. It picks a
deterministic scenario each asset actually supports:

  - has schema fields  -> stale schema hash        -> detects SCHEMA_DRIFT
  - else has an owner   -> different last owner      -> detects OWNER_CHANGED
  - else                -> last checked 48h ago      -> detects FRESHNESS_STALE

Then ``POST /scan`` reads live metadata, detects the change, explains it, and
writes a tag + assertion back to the asset. Requires a live DataHub
(``DATAHUB_TOKEN`` set); run the SSH tunnel first.

Usage:  .\.venv\Scripts\python seed_live.py
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path


def _load_env(path: str = ".env") -> None:
    """Load KEY=VALUE lines from .env into the process env (comments stripped).

    Kept tiny and dependency-free; runs before app.config is imported so the
    DataHub token/URL are visible. Existing env vars win.
    """
    env_file = Path(path)
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.split(" #", 1)[0].strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


_load_env()

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.config import DATABASE_URL, DATAHUB_TOKEN  # noqa: E402
from app.integrations.datahub import create_datahub_client  # noqa: E402
from app.monitored_assets import (  # noqa: E402
    DISCOVERY_LIMIT,
    DISCOVERY_QUERIES,
    WATCHLIST,
)
from app.repository.models import Base, MonitoringStateModel  # noqa: E402

STALE_HASH = "dataco-stale-000"
FORMER_OWNER = "dataco-former-owner"


def _resolve_urns(datahub) -> list[str]:
    if WATCHLIST:
        return list(WATCHLIST)
    found: list[str] = []
    for q in DISCOVERY_QUERIES:
        for asset in datahub.search(q):
            if asset.urn not in found:
                found.append(asset.urn)
            if len(found) >= DISCOVERY_LIMIT:
                return found
    return found


def _baseline_for(urn: str, meta) -> MonitoringStateModel:
    now = datetime.now()
    if meta is None:
        # Asset didn't resolve — still seed a freshness baseline so /scan has
        # something to report rather than silently skipping.
        return MonitoringStateModel(
            asset_id=urn, last_schema_hash="", last_owner=None,
            last_checked_at=now - timedelta(hours=48),
        )
    if meta.schema_fields:
        return MonitoringStateModel(
            asset_id=urn, last_schema_hash=STALE_HASH, last_owner=meta.owner,
            last_checked_at=now,
        )
    if meta.owner:
        return MonitoringStateModel(
            asset_id=urn, last_schema_hash="", last_owner=FORMER_OWNER,
            last_checked_at=now,
        )
    return MonitoringStateModel(
        asset_id=urn, last_schema_hash="", last_owner=None,
        last_checked_at=now - timedelta(hours=48),
    )


def seed_live(db_url: str = DATABASE_URL) -> None:
    if not DATAHUB_TOKEN:
        raise SystemExit(
            "DATAHUB_TOKEN is not set — seed_live needs a live DataHub. "
            "Start the SSH tunnel and pass --env-file .env / export the token."
        )

    datahub = create_datahub_client()
    urns = _resolve_urns(datahub)
    if not urns:
        raise SystemExit("No assets to monitor (WATCHLIST empty, none discovered).")

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        for urn in urns:
            meta = datahub.get_asset(urn)
            state = _baseline_for(urn, meta)
            merged = session.merge(state)  # upsert by asset_id PK
            session.add(merged)
            kind = "schema_drift" if (meta and meta.schema_fields) else (
                "owner_changed" if (meta and meta.owner) else "freshness_stale"
            )
            print(f"  primed {urn} -> will detect {kind}")
        session.commit()

    print(f"Primed {len(urns)} live asset(s). Run POST /scan to detect + write back.")


if __name__ == "__main__":
    seed_live()
