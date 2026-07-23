from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_datahub
from app.integrations.datahub import DataHubClient
from app.schemas.responses import AssetResponse, LineageResponse

router = APIRouter()


@router.get("/asset/{urn:path}", response_model=AssetResponse)
def get_asset(urn: str, datahub: DataHubClient = Depends(get_datahub)):
    asset = datahub.get_asset(urn)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return AssetResponse(
        urn=asset.urn,
        name=asset.name,
        description=asset.description,
        owner=asset.owner,
        schema_fields=[{"name": f.name, "type": f.type} for f in asset.schema_fields],
        freshness=asset.freshness,
        tags=asset.tags,
        docs=asset.docs,
    )


@router.get("/lineage/{urn:path}", response_model=LineageResponse)
def get_lineage(urn: str, datahub: DataHubClient = Depends(get_datahub)):
    lineage = datahub.get_lineage(urn)
    return LineageResponse(
        upstream=[{"id": n.urn, "name": n.name} for n in lineage.upstream],
        downstream=[{"id": n.urn, "name": n.name} for n in lineage.downstream],
    )
