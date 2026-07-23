"""Seed the database with demo data for the hackathon presentation."""

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.repository.models import Base, MonitoringStateModel
from tests.factories import DEMO_ASSETS, build_issue


def seed(db_url: str = "sqlite:///./dataco.db") -> None:
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        for a in DEMO_ASSETS:
            issue = build_issue(
                asset_id=a["asset_id"],
                asset_name=a["asset_name"],
                issue_type=a["issue_type"],
                severity=a["severity"],
                owner=a["owner"],
                blast_radius=a["blast_radius"],
                impacted_assets=a["impacted"],
                created_at=datetime.now(UTC),
            )
            session.add(issue)

            session.add(
                MonitoringStateModel(
                    asset_id=a["asset_id"],
                    last_schema_hash="abc123",
                    last_owner="lab-team",
                    last_checked_at=datetime.now(UTC),
                )
            )

        session.commit()

    print(f"Seeded {len(DEMO_ASSETS)} issues.")


if __name__ == "__main__":
    seed()
