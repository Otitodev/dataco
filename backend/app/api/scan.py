from fastapi import APIRouter, Depends

from app.deps import get_datahub, get_llm, get_repo
from app.integrations.datahub import DataHubClient
from app.integrations.llm import LLMClient
from app.monitored_assets import WATCHLIST
from app.repository.store import Repository
from app.schemas.responses import ScanRequest, ScanResultResponse
from app.services.scan import scan_all

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
    urns = (req.urns if req else None) or repo.list_monitored_urns() or WATCHLIST
    results = scan_all(urns, datahub=datahub, repo=repo, llm=llm)
    return [ScanResultResponse(**vars(r)) for r in results]
