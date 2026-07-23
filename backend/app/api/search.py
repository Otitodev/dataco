from fastapi import APIRouter, Depends, Query

from app.deps import get_datahub
from app.integrations.datahub import DataHubClient
from app.schemas.responses import SearchResultResponse

router = APIRouter()


@router.get("/search", response_model=list[SearchResultResponse])
def search(q: str = Query(...), datahub: DataHubClient = Depends(get_datahub)):
    results = datahub.search(q)
    return [
        SearchResultResponse(
            urn=r.urn,
            name=r.name,
            description=r.description,
            owner=r.owner,
        )
        for r in results
    ]
