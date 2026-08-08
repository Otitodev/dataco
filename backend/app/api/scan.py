from fastapi import APIRouter, Depends

from app.deps import get_datahub, get_llm, get_repo
from app.integrations.datahub import DataHubClient
from app.integrations.llm import LLMClient
from app.repository.store import Repository
from app.schemas.responses import (
    ScanRequest,
    ScanResultResponse,
    ScanStatusResponse,
)
from app.services import scheduler
from app.services.scan import resolve_urns, scan_all

router = APIRouter()


@router.post("/scan", response_model=list[ScanResultResponse])
def scan(
    req: ScanRequest | None = None,
    repo: Repository = Depends(get_repo),
    llm: LLMClient = Depends(get_llm),
    datahub: DataHubClient = Depends(get_datahub),
):
    """Run the scan agent over a set of assets.

    URN resolution order: explicit ``req.urns`` → assets already primed in the
    monitoring baseline (via ``seed_live.py``) → the static ``WATCHLIST``.
    """
    urns = resolve_urns(repo, req.urns if req else None)
    results = scan_all(urns, datahub=datahub, repo=repo, llm=llm)
    return [ScanResultResponse(**vars(r)) for r in results]


@router.get("/scan/status", response_model=ScanStatusResponse)
def scan_status(repo: Repository = Depends(get_repo)):
    """Current state of the background scan scheduler (autonomous loop)."""
    state = scheduler.get_status()
    return ScanStatusResponse(
        enabled=state.enabled,
        interval_seconds=state.interval_seconds,
        last_run_at=state.last_run_at,
        last_scanned=state.last_scanned,
        last_detected=state.last_detected,
        watch_count=len(resolve_urns(repo)),
    )
