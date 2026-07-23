from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_datahub, get_repo
from app.integrations.datahub import DataHubClient
from app.repository.models import IssueNoteRecord
from app.repository.store import Repository
from app.schemas.responses import (
    IssueResponse,
    NoteCreateRequest,
    NoteResponse,
    StatusUpdateRequest,
    WriteBackResponse,
)
from app.services.writeback import write_back_issue

router = APIRouter()


@router.patch("/issue/{issue_id}", response_model=IssueResponse)
def update_issue_status(
    issue_id: str, req: StatusUpdateRequest, repo: Repository = Depends(get_repo)
):
    issue = repo.update_issue_status(issue_id, req.status)
    if issue is None:
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
    )


@router.post("/issue/{issue_id}/writeback", response_model=WriteBackResponse)
def write_back(
    issue_id: str,
    repo: Repository = Depends(get_repo),
    datahub: DataHubClient = Depends(get_datahub),
):
    issue = repo.get_issue(issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    result = write_back_issue(datahub, issue)
    repo.save_writeback(
        issue.id, tag_urn=result.tag_urn, assertion_urn=result.assertion_urn
    )
    return WriteBackResponse(
        issue_id=issue.id,
        ok=result.ok,
        tag_urn=result.tag_urn,
        assertion_urn=result.assertion_urn,
        detail=result.detail,
    )


@router.post("/issue/{issue_id}/note", response_model=NoteResponse)
def add_note(
    issue_id: str, req: NoteCreateRequest, repo: Repository = Depends(get_repo)
):
    note = IssueNoteRecord(
        issue_id=issue_id, note_text=req.note_text, author=req.author
    )
    saved = repo.create_note(note)
    return NoteResponse(
        id=saved.id,
        issue_id=saved.issue_id,
        note_text=saved.note_text,
        author=saved.author,
        created_at=saved.created_at,
    )


@router.get("/issue/{issue_id}/notes", response_model=list[NoteResponse])
def list_notes(issue_id: str, repo: Repository = Depends(get_repo)):
    notes = repo.get_notes_for_issue(issue_id)
    return [
        NoteResponse(
            id=n.id,
            issue_id=n.issue_id,
            note_text=n.note_text,
            author=n.author,
            created_at=n.created_at,
        )
        for n in notes
    ]
