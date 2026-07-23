from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_datahub, get_llm, get_repo
from app.integrations.datahub import DataHubClient
from app.integrations.llm import LLMClient
from app.repository.store import Repository
from app.schemas.responses import (
    BriefRequest,
    BriefResponse,
    ExplainRequest,
    ExplanationResponse,
)
from app.services.reasoning import brief_issue, explain_issue

router = APIRouter()


@router.post("/explain", response_model=ExplanationResponse)
def explain(
    req: ExplainRequest,
    repo: Repository = Depends(get_repo),
    llm: LLMClient = Depends(get_llm),
    datahub: DataHubClient = Depends(get_datahub),
):
    issue = repo.get_issue(req.issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")

    result = explain_issue(issue, repo=repo, llm=llm, datahub=datahub)
    return ExplanationResponse(
        summary=result.summary,
        likely_cause=result.likely_cause,
        impacted_assets=result.impacted_assets,
        confidence=result.confidence,
        recommended_action=result.recommended_action,
    )


@router.post("/brief", response_model=BriefResponse)
def generate_brief(
    req: BriefRequest,
    repo: Repository = Depends(get_repo),
    llm: LLMClient = Depends(get_llm),
    datahub: DataHubClient = Depends(get_datahub),
):
    issue = repo.get_issue(req.issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")

    saved = brief_issue(issue, repo=repo, llm=llm, datahub=datahub)
    return BriefResponse(
        id=saved.id,
        issue_id=saved.issue_id,
        subject=saved.subject or "",
        what_happened=saved.what_happened or "",
        what_is_affected=saved.get_affected(),
        who_to_contact=saved.who_to_contact or "",
        next_step=saved.next_step or "",
        estimated_impact=saved.estimated_impact or "medium",
        generated_at=saved.generated_at,
    )
