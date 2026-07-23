"""Regenerate the sample outputs in this folder.

Runs the full Dataco stack in-process against the offline fake DataHub + stub
LLM, so it is deterministic and needs no running server, no secrets, and no live
DataHub. From the repo root:

    backend\\.venv\\Scripts\\python examples\\generate_examples.py
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.environ["DATAHUB_PROVIDER"] = "fake"
os.environ["LLM_PROVIDER"] = "stub"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.deps import get_datahub, get_db, get_llm, get_repo  # noqa: E402
from app.main import create_app  # noqa: E402
from app.repository.models import Base, MonitoringStateModel  # noqa: E402
from app.repository.store import Repository  # noqa: E402
from app.services.scan import scan_asset  # noqa: E402
from tests.factories import DEMO_ASSETS, build_issue  # noqa: E402
from tests.fakes import DEMO_DATA, FakeDataHubClient, StubLLMClient  # noqa: E402

OUT = ROOT / "examples"
URN = "urn:dataco:lab_ingestion_feed"


def _seeded_repo(session):
    repo = Repository(session)
    for a in DEMO_ASSETS:
        repo.create_issue(
            build_issue(
                asset_id=a["asset_id"],
                asset_name=a["asset_name"],
                issue_type=a["issue_type"],
                severity=a["severity"],
                owner=a["owner"],
                blast_radius=a["blast_radius"],
                impacted_assets=a["impacted"],
            )
        )
    return repo


def _dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, default=str))
    print("wrote examples/" + name)


def main():
    import tempfile

    db_path = Path(tempfile.gettempdir()) / "dataco_examples.db"
    db_path.unlink(missing_ok=True)
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(engine)()
    repo = _seeded_repo(session)

    app = create_app()
    app.dependency_overrides[get_datahub] = lambda: FakeDataHubClient(**DEMO_DATA)
    app.dependency_overrides[get_llm] = lambda: StubLLMClient()

    def _db():
        yield session

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_repo] = lambda: repo
    client = TestClient(app)

    dashboard = client.get("/dashboard").json()
    issue_id = dashboard[0]["id"]
    _dump("dashboard.json", dashboard)
    _dump("explain-schema-drift.json",
          client.post("/explain", json={"issue_id": issue_id}).json())
    _dump("brief-schema-drift.json",
          client.post("/brief", json={"issue_id": issue_id}).json())
    _dump("writeback.json",
          client.post(f"/issue/{issue_id}/writeback").json())

    # The autonomous scan: prime a stale baseline, then detect + write back.
    repo.upsert_monitoring_state(
        MonitoringStateModel(
            asset_id=URN, last_schema_hash="stale-000", last_owner="lab-team"
        )
    )
    scan = scan_asset(
        URN,
        datahub=FakeDataHubClient(**DEMO_DATA),
        repo=repo,
        llm=StubLLMClient(),
    )
    _dump("scan-result.json", vars(scan))


if __name__ == "__main__":
    main()
