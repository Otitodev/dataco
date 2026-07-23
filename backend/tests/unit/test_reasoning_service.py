from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.repository.models import Base
from app.repository.store import Repository
from app.services.reasoning import brief_issue, explain_issue
from tests.factories import build_issue
from tests.fakes import DEMO_DATA, FakeDataHubClient

URN = "urn:dataco:lab_ingestion_feed"


def _repo():
    eng = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(eng)
    return Repository(sessionmaker(eng)())


class _BoomLLM:
    """Simulates a real provider failing (e.g. 401 invalid/expired key)."""

    def explain(self, context):
        raise RuntimeError("401 invalid x-api-key")

    def brief(self, context):
        raise RuntimeError("401 invalid x-api-key")


def test_explain_falls_back_to_stub_on_llm_error():
    repo = _repo()
    issue = repo.create_issue(
        build_issue(asset_id=URN, asset_name="lab_ingestion_feed")
    )
    dh = FakeDataHubClient(**DEMO_DATA)

    result = explain_issue(issue, repo=repo, llm=_BoomLLM(), datahub=dh)

    assert result.summary  # got the deterministic stub, not a crash
    assert repo.get_issue(issue.id).summary  # persisted


def test_brief_falls_back_to_stub_on_llm_error():
    repo = _repo()
    issue = repo.create_issue(
        build_issue(asset_id=URN, asset_name="lab_ingestion_feed")
    )
    dh = FakeDataHubClient(**DEMO_DATA)

    brief = brief_issue(issue, repo=repo, llm=_BoomLLM(), datahub=dh)

    assert brief.subject  # stub brief persisted rather than raising
