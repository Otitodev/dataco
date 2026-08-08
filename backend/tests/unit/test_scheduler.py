"""Unit tests for the continuous scan scheduler.

These exercise the loop's building blocks — ``resolve_urns`` precedence and a
single ``run_once`` tick — without real sleeping or a live DataHub. The
scheduler's module state is snapshotted and restored so these tests never leak
into the API-level status test (which asserts the default *disabled* state).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.monitored_assets import WATCHLIST
from app.repository.models import Base, MonitoringStateModel
from app.repository.store import Repository
from app.services import scheduler
from app.services.scan import resolve_urns
from tests.fakes import DEMO_DATA, FakeDataHubClient, StubLLMClient


def test_resolve_urns_precedence(repo):
    # No explicit, no primed state -> the static WATCHLIST.
    assert resolve_urns(repo) == WATCHLIST

    # Explicit request always wins.
    assert resolve_urns(repo, ["urn:x"]) == ["urn:x"]

    # A primed monitoring baseline is used ahead of the WATCHLIST.
    repo.upsert_monitoring_state(MonitoringStateModel(asset_id="urn:primed"))
    assert resolve_urns(repo) == ["urn:primed"]


@pytest.fixture
def scheduler_env(monkeypatch):
    """Point the scheduler at a temp DB + fake clients; restore state after."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    session_cls = sessionmaker(engine)

    monkeypatch.setattr(scheduler, "SessionLocal", session_cls)
    monkeypatch.setattr(
        scheduler, "get_datahub", lambda: FakeDataHubClient(**DEMO_DATA)
    )
    monkeypatch.setattr(scheduler, "get_llm", lambda: StubLLMClient())

    original_state = scheduler._state
    scheduler._state = scheduler.SchedulerState()
    try:
        yield session_cls
    finally:
        scheduler._state = original_state


def test_run_once_updates_state(scheduler_env):
    session_cls = scheduler_env
    # Prime the fake's asset so the scan resolves to a real (fake) URN.
    repo = Repository(session_cls())
    repo.upsert_monitoring_state(
        MonitoringStateModel(asset_id="urn:dataco:lab_ingestion_feed")
    )

    assert scheduler.get_status().last_run_at is None

    scheduler.run_once()

    state = scheduler.get_status()
    assert state.last_run_at is not None
    assert state.last_scanned == 1  # one primed asset scanned
    assert state.last_detected >= 0


def test_run_once_survives_a_failing_cycle(scheduler_env, monkeypatch):
    # A crash inside the cycle must be swallowed so the loop lives on.
    def boom(*args, **kwargs):
        raise RuntimeError("datahub exploded")

    monkeypatch.setattr(scheduler, "scan_all", boom)
    scheduler.run_once()  # must not raise
