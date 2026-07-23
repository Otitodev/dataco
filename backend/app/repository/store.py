from datetime import UTC, datetime

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.repository.models import (
    BriefRecord,
    IssueNoteRecord,
    IssueRecord,
    MonitoringStateModel,
)

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class Repository:
    def __init__(self, session: Session):
        self.session = session

    def create_issue(self, issue: IssueRecord) -> IssueRecord:
        self.session.add(issue)
        self.session.commit()
        return issue

    def get_issue(self, issue_id: str) -> IssueRecord | None:
        return self.session.get(IssueRecord, issue_id)

    def find_active_issue(
        self, asset_id: str, issue_type: str
    ) -> IssueRecord | None:
        """An open issue for this asset + type, if one is already tracked."""
        stmt = (
            select(IssueRecord)
            .where(
                IssueRecord.asset_id == asset_id,
                IssueRecord.issue_type == issue_type,
                IssueRecord.status.in_(["active", "investigating"]),
            )
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def list_active_issues(self) -> list[IssueRecord]:
        severity_case = case(SEVERITY_ORDER, value=IssueRecord.severity)
        stmt = (
            select(IssueRecord)
            .where(IssueRecord.status.in_(["active", "investigating"]))
            .order_by(severity_case, IssueRecord.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def update_issue_status(self, issue_id: str, status: str) -> IssueRecord | None:
        issue = self.session.get(IssueRecord, issue_id)
        if issue is None:
            return None
        issue.status = status
        if status == "resolved":
            issue.resolved_at = datetime.now(UTC)
        self.session.commit()
        return issue

    def save_explanation(
        self,
        issue_id: str,
        *,
        summary: str,
        likely_cause: str,
        impacted_assets: list[str],
        confidence: str,
        blast_radius: int | None = None,
    ) -> IssueRecord | None:
        issue = self.session.get(IssueRecord, issue_id)
        if issue is None:
            return None
        issue.summary = summary
        issue.likely_cause = likely_cause
        issue.set_impacted(impacted_assets)
        issue.confidence = confidence
        if blast_radius is not None:
            issue.blast_radius = blast_radius
        self.session.commit()
        return issue

    def save_writeback(
        self,
        issue_id: str,
        *,
        tag_urn: str | None,
        assertion_urn: str | None,
    ) -> IssueRecord | None:
        issue = self.session.get(IssueRecord, issue_id)
        if issue is None:
            return None
        issue.datahub_tag_urn = tag_urn
        issue.datahub_assertion_urn = assertion_urn
        issue.written_back_at = datetime.now(UTC)
        self.session.commit()
        return issue

    def create_brief(self, brief: BriefRecord) -> BriefRecord:
        self.session.add(brief)
        self.session.commit()
        return brief

    def get_briefs_for_issue(self, issue_id: str) -> list[BriefRecord]:
        stmt = select(BriefRecord).where(BriefRecord.issue_id == issue_id)
        return list(self.session.scalars(stmt))

    def create_note(self, note: IssueNoteRecord) -> IssueNoteRecord:
        self.session.add(note)
        self.session.commit()
        return note

    def get_notes_for_issue(self, issue_id: str) -> list[IssueNoteRecord]:
        stmt = select(IssueNoteRecord).where(IssueNoteRecord.issue_id == issue_id)
        return list(self.session.scalars(stmt))

    def get_monitoring_state(self, asset_id: str) -> MonitoringStateModel | None:
        return self.session.get(MonitoringStateModel, asset_id)

    def list_monitored_urns(self) -> list[str]:
        return list(self.session.scalars(select(MonitoringStateModel.asset_id)))

    def upsert_monitoring_state(
        self, state: MonitoringStateModel
    ) -> MonitoringStateModel:
        existing = self.session.get(MonitoringStateModel, state.asset_id)
        if existing:
            existing.last_checked_at = state.last_checked_at
            existing.freshness_status = state.freshness_status
            existing.last_schema_hash = state.last_schema_hash
            existing.last_owner = state.last_owner
            existing.consecutive_failures = (
                state.consecutive_failures
                if state.consecutive_failures is not None
                else existing.consecutive_failures
            )
        else:
            self.session.add(state)
        self.session.commit()
        return existing or state
