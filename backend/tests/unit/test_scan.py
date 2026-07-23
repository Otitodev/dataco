from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.repository.models import Base, MonitoringStateModel
from app.repository.store import Repository
from app.services.scan import scan_asset
from tests.fakes import DEMO_DATA, FakeDataHubClient, StubLLMClient

URN = "urn:dataco:lab_ingestion_feed"


def _repo():
    eng = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(eng)
    return Repository(sessionmaker(eng)())


def test_scan_detects_schema_drift_and_writes_back():
    repo = _repo()
    repo.upsert_monitoring_state(
        MonitoringStateModel(
            asset_id=URN, last_schema_hash="stale-000", last_owner="lab-team"
        )
    )
    dh = FakeDataHubClient(**DEMO_DATA)

    result = scan_asset(URN, datahub=dh, repo=repo, llm=StubLLMClient())

    assert result.detected
    assert result.issue_type == "schema_drift"
    assert result.severity == "critical"  # blast_radius 4
    assert result.tag_urn and result.assertion_urn

    issue = repo.get_issue(result.issue_id)
    assert issue.summary  # grounded explanation persisted
    assert issue.confidence == "high"
    assert issue.datahub_tag_urn == result.tag_urn
    assert issue.written_back_at is not None


def test_scan_self_heals_writeback_for_untracked_issue():
    from tests.factories import build_issue

    repo = _repo()
    # An open issue exists but was never written back (written_back_at is None)...
    repo.create_issue(build_issue(asset_id=URN, issue_type="schema_drift"))
    # ...and the baseline still shows drift (stale hash).
    repo.upsert_monitoring_state(
        MonitoringStateModel(
            asset_id=URN, last_schema_hash="stale-000", last_owner="lab-team"
        )
    )
    dh = FakeDataHubClient(**DEMO_DATA)

    result = scan_asset(URN, datahub=dh, repo=repo, llm=StubLLMClient())

    assert not result.detected
    assert result.detail == "already tracked; wrote back"
    assert len(repo.list_active_issues()) == 1  # no duplicate
    assert result.tag_urn and result.assertion_urn  # write-back completed
    assert [w[0] for w in dh.writes] == ["tag", "assertion"]


def test_scan_skips_writeback_when_already_written():
    from tests.factories import build_issue

    repo = _repo()
    issue = repo.create_issue(build_issue(asset_id=URN, issue_type="schema_drift"))
    repo.save_writeback(
        issue.id,
        tag_urn="urn:li:tag:trust:schema_drift",
        assertion_urn="urn:li:assertion:x",
    )
    repo.upsert_monitoring_state(
        MonitoringStateModel(
            asset_id=URN, last_schema_hash="stale-000", last_owner="lab-team"
        )
    )
    dh = FakeDataHubClient(**DEMO_DATA)

    result = scan_asset(URN, datahub=dh, repo=repo, llm=StubLLMClient())

    assert not result.detected
    assert result.detail == "already tracked"
    assert dh.writes == []  # nothing re-written


def test_scan_no_prior_state_sets_baseline_no_issue():
    repo = _repo()
    dh = FakeDataHubClient(**DEMO_DATA)

    result = scan_asset(URN, datahub=dh, repo=repo, llm=StubLLMClient())

    assert not result.detected
    assert result.detail == "no issue"
    assert repo.get_monitoring_state(URN) is not None  # baseline established


def test_scan_asset_not_found_is_graceful():
    repo = _repo()
    dh = FakeDataHubClient(**DEMO_DATA)

    result = scan_asset(
        "urn:dataco:missing", datahub=dh, repo=repo, llm=StubLLMClient()
    )

    assert not result.detected
    assert result.detail == "asset not found"
