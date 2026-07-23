from fastapi import APIRouter, Depends

from app.deps import get_repo
from app.repository.store import Repository
from app.schemas.responses import IssueResponse

router = APIRouter()


@router.get("/dashboard", response_model=list[IssueResponse])
def list_issues(repo: Repository = Depends(get_repo)):
    issues = repo.list_active_issues()
    return [
        IssueResponse(
            id=i.id,
            asset_id=i.asset_id,
            asset_name=i.asset_name,
            issue_type=i.issue_type,
            severity=i.severity,
            status=i.status,
            summary=i.summary,
            likely_cause=i.likely_cause,
            impacted_assets=i.get_impacted(),
            blast_radius=i.blast_radius,
            owner=i.owner,
            confidence=i.confidence,
            created_at=i.created_at,
            updated_at=i.updated_at,
            resolved_at=i.resolved_at,
            datahub_tag_urn=i.datahub_tag_urn,
            datahub_assertion_urn=i.datahub_assertion_urn,
            written_back_at=i.written_back_at,
        )
        for i in issues
    ]


@router.get("/issue/{issue_id}", response_model=IssueResponse)
def get_issue(issue_id: str, repo: Repository = Depends(get_repo)):
    issue = repo.get_issue(issue_id)
    if issue is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Issue not found")
    return IssueResponse(
        id=issue.id,
        asset_id=issue.asset_id,
        asset_name=issue.asset_name,
        issue_type=issue.issue_type,
        severity=issue.severity,
        status=issue.status,
        summary=issue.summary,
        likely_cause=issue.likely_cause,
        impacted_assets=issue.get_impacted(),
        blast_radius=issue.blast_radius,
        owner=issue.owner,
        confidence=issue.confidence,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
        resolved_at=issue.resolved_at,
        datahub_tag_urn=issue.datahub_tag_urn,
        datahub_assertion_urn=issue.datahub_assertion_urn,
        written_back_at=issue.written_back_at,
    )
