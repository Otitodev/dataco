from datetime import datetime

from pydantic import BaseModel


class IssueResponse(BaseModel):
    id: str
    asset_id: str
    asset_name: str
    issue_type: str
    severity: str
    status: str
    summary: str | None = None
    likely_cause: str | None = None
    impacted_assets: list[str] = []
    blast_radius: int = 0
    owner: str | None = None
    confidence: str | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    datahub_tag_urn: str | None = None
    datahub_assertion_urn: str | None = None
    written_back_at: datetime | None = None

    model_config = {"from_attributes": True}


class AssetResponse(BaseModel):
    urn: str
    name: str
    description: str = ""
    owner: str | None = None
    schema_fields: list[dict] = []
    freshness: str | None = None
    tags: list[str] = []
    docs: str | None = None


class LineageResponse(BaseModel):
    upstream: list[dict]
    downstream: list[dict]


class ExplanationResponse(BaseModel):
    summary: str
    likely_cause: str
    impacted_assets: list[str]
    confidence: str
    recommended_action: str


class BriefResponse(BaseModel):
    id: str
    issue_id: str
    subject: str
    what_happened: str
    what_is_affected: list[str]
    who_to_contact: str
    next_step: str
    estimated_impact: str
    generated_at: datetime

    model_config = {"from_attributes": True}


class ScanRequest(BaseModel):
    urns: list[str] | None = None


class ScanResultResponse(BaseModel):
    urn: str
    detected: bool
    issue_id: str | None = None
    issue_type: str | None = None
    severity: str | None = None
    tag_urn: str | None = None
    assertion_urn: str | None = None
    detail: str = ""


class WriteBackResponse(BaseModel):
    issue_id: str
    ok: bool
    tag_urn: str | None = None
    assertion_urn: str | None = None
    detail: str = ""


class NoteResponse(BaseModel):
    id: str
    issue_id: str
    note_text: str
    author: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SearchResultResponse(BaseModel):
    urn: str
    name: str
    description: str = ""
    owner: str | None = None


class StatusUpdateRequest(BaseModel):
    status: str


class ExplainRequest(BaseModel):
    issue_id: str


class BriefRequest(BaseModel):
    issue_id: str


class NoteCreateRequest(BaseModel):
    note_text: str
    author: str | None = None
