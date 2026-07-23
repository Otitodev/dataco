
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.repository.models import (
    Base,
    BriefRecord,
    IssueNoteRecord,
    MonitoringStateModel,
)
from app.repository.store import Repository
from tests.factories import build_issue


@pytest.fixture
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_cls = sessionmaker(engine)
    session = session_cls()
    yield Repository(session)
    session.close()


class TestIssueCRUD:
    def test_create_and_get_issue(self, repo):
        issue = build_issue(asset_id="urn:test", severity="high")
        created = repo.create_issue(issue)
        fetched = repo.get_issue(created.id)
        assert fetched is not None
        assert fetched.asset_id == "urn:test"
        assert fetched.severity == "high"

    def test_list_active_issues_sorted_by_severity(self, repo):
        low = build_issue(asset_id="urn:low", severity="low")
        critical = build_issue(asset_id="urn:crit", severity="critical")
        medium = build_issue(asset_id="urn:med", severity="medium")
        repo.create_issue(low)
        repo.create_issue(critical)
        repo.create_issue(medium)

        issues = repo.list_active_issues()
        assert len(issues) == 3
        assert issues[0].severity == "critical"
        assert issues[1].severity == "medium"
        assert issues[2].severity == "low"

    def test_resolved_issues_not_in_active_list(self, repo):
        issue = build_issue(status="resolved")
        repo.create_issue(issue)
        assert len(repo.list_active_issues()) == 0

    def test_update_issue_status(self, repo):
        issue = build_issue(status="active")
        created = repo.create_issue(issue)
        updated = repo.update_issue_status(created.id, "investigating")
        assert updated is not None
        assert updated.status == "investigating"

    def test_resolve_sets_resolved_at(self, repo):
        issue = build_issue()
        created = repo.create_issue(issue)
        updated = repo.update_issue_status(created.id, "resolved")
        assert updated.resolved_at is not None


class TestBriefCRUD:
    def test_create_and_list_briefs(self, repo):
        issue = repo.create_issue(build_issue(asset_id="urn:b"))
        brief = BriefRecord(issue_id=issue.id, subject="Test", estimated_impact="high")
        repo.create_brief(brief)

        briefs = repo.get_briefs_for_issue(issue.id)
        assert len(briefs) == 1
        assert briefs[0].subject == "Test"


class TestNoteCRUD:
    def test_create_and_list_notes(self, repo):
        issue = repo.create_issue(build_issue(asset_id="urn:n"))
        note = IssueNoteRecord(
            issue_id=issue.id, note_text="Looking into this", author="Ana"
        )
        repo.create_note(note)

        notes = repo.get_notes_for_issue(issue.id)
        assert len(notes) == 1
        assert notes[0].note_text == "Looking into this"


class TestMonitoringState:
    def test_upsert_creates_new_state(self, repo):
        state = MonitoringStateModel(asset_id="urn:m", last_schema_hash="abc")
        repo.upsert_monitoring_state(state)
        fetched = repo.get_monitoring_state("urn:m")
        assert fetched is not None
        assert fetched.last_schema_hash == "abc"

    def test_upsert_updates_existing_state(self, repo):
        state = MonitoringStateModel(
            asset_id="urn:m2", last_schema_hash="v1", last_owner="a"
        )
        repo.upsert_monitoring_state(state)

        updated = MonitoringStateModel(
            asset_id="urn:m2", last_schema_hash="v2", last_owner="b"
        )
        repo.upsert_monitoring_state(updated)

        fetched = repo.get_monitoring_state("urn:m2")
        assert fetched.last_schema_hash == "v2"
        assert fetched.last_owner == "b"
