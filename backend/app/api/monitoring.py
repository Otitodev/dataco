from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import get_datahub, get_repo
from app.integrations.datahub import DataHubClient
from app.repository.store import Repository
from app.schemas.responses import AddMonitoredRequest, MonitoredAssetResponse
from app.services.monitoring import (
    add_monitored_asset,
    list_monitored_assets,
    remove_monitored_asset,
)

router = APIRouter()


@router.get("/monitored", response_model=list[MonitoredAssetResponse])
def list_monitored(
    repo: Repository = Depends(get_repo),
    datahub: DataHubClient = Depends(get_datahub),
):
    """The assets Dataco is currently watching."""
    assets = list_monitored_assets(datahub=datahub, repo=repo)
    return [MonitoredAssetResponse(**vars(a)) for a in assets]


@router.post("/monitored", response_model=MonitoredAssetResponse)
def add_monitored(
    req: AddMonitoredRequest,
    repo: Repository = Depends(get_repo),
    datahub: DataHubClient = Depends(get_datahub),
):
    """Start watching an asset — primes a baseline at its current state."""
    asset = add_monitored_asset(req.urn, datahub=datahub, repo=repo)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found in DataHub")
    return MonitoredAssetResponse(**vars(asset))


@router.delete("/monitored")
def remove_monitored(
    urn: str = Query(...), repo: Repository = Depends(get_repo)
):
    """Stop watching an asset."""
    if not remove_monitored_asset(urn, repo=repo):
        raise HTTPException(status_code=404, detail="Asset is not being monitored")
    return {"ok": True, "urn": urn}
