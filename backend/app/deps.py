from collections.abc import Generator

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import DATABASE_URL
from app.integrations.datahub import DataHubClient
from app.integrations.llm import LLMClient
from app.repository.store import Repository

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_datahub_client: DataHubClient | None = None
_llm_client: LLMClient | None = None


def set_datahub_client(client: DataHubClient) -> None:
    global _datahub_client
    _datahub_client = client


def get_datahub() -> DataHubClient:
    if _datahub_client is None:
        from app.integrations.datahub import create_datahub_client
        return create_datahub_client()
    return _datahub_client


def set_llm_client(client: LLMClient) -> None:
    global _llm_client
    _llm_client = client


def get_llm() -> LLMClient:
    if _llm_client is None:
        from app.integrations.llm import create_llm_client
        return create_llm_client()
    return _llm_client


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_repo(db: Session = Depends(get_db)) -> Repository:
    return Repository(db)
