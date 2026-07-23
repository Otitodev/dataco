import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.deps import get_datahub, get_db, get_llm, get_repo
from app.main import create_app
from app.repository.models import Base
from app.repository.store import Repository
from tests.factories import DEMO_ASSETS, build_issue


@pytest.fixture
def db_session():
    import os
    import tempfile
    import uuid
    db_path = os.path.join(tempfile.gettempdir(), f"dataco_test_{uuid.uuid4().hex}.db")
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    session_cls = sessionmaker(engine)
    session = session_cls()
    yield session
    session.close()
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def repo(db_session):
    return Repository(db_session)


@pytest.fixture
def seeded_repo(repo):
    for a in DEMO_ASSETS:
        issue = build_issue(
            asset_id=a["asset_id"],
            asset_name=a["asset_name"],
            issue_type=a["issue_type"],
            severity=a["severity"],
            owner=a["owner"],
            blast_radius=a["blast_radius"],
            impacted_assets=a["impacted"],
        )
        repo.create_issue(issue)
    return repo


@pytest.fixture
def client(seeded_repo, db_session):
    from tests.fakes import DEMO_DATA, FakeDataHubClient, StubLLMClient

    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_datahub] = lambda: FakeDataHubClient(**DEMO_DATA)
    app.dependency_overrides[get_llm] = lambda: StubLLMClient()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_repo] = lambda: seeded_repo
    return TestClient(app)
