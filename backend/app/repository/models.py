import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class IssueRecord(Base):
    __tablename__ = "issues"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    asset_id: Mapped[str] = mapped_column(String, nullable=False)
    asset_name: Mapped[str] = mapped_column(String, nullable=False)
    issue_type: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    likely_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    impacted_assets: Mapped[str | None] = mapped_column(Text, nullable=True)
    blast_radius: Mapped[int] = mapped_column(Integer, default=0)
    owner: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Write-back provenance: the DataHub artifacts Dataco created for this issue.
    datahub_tag_urn: Mapped[str | None] = mapped_column(String, nullable=True)
    datahub_assertion_urn: Mapped[str | None] = mapped_column(String, nullable=True)
    written_back_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    notes: Mapped[list["IssueNoteRecord"]] = relationship(
        "IssueNoteRecord", back_populates="issue", order_by="IssueNoteRecord.created_at"
    )
    briefs: Mapped[list["BriefRecord"]] = relationship(
        "BriefRecord", back_populates="issue", order_by="BriefRecord.generated_at"
    )

    def set_impacted(self, assets: list[str]) -> None:
        self.impacted_assets = json.dumps(assets)

    def get_impacted(self) -> list[str]:
        return json.loads(self.impacted_assets or "[]")


class BriefRecord(Base):
    __tablename__ = "briefs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    issue_id: Mapped[str] = mapped_column(
        String, ForeignKey("issues.id"), nullable=False
    )
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    what_happened: Mapped[str | None] = mapped_column(Text, nullable=True)
    what_is_affected: Mapped[str | None] = mapped_column(Text, nullable=True)
    who_to_contact: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_impact: Mapped[str | None] = mapped_column(String, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    issue: Mapped[IssueRecord] = relationship("IssueRecord", back_populates="briefs")

    def set_affected(self, assets: list[str]) -> None:
        self.what_is_affected = json.dumps(assets)

    def get_affected(self) -> list[str]:
        return json.loads(self.what_is_affected or "[]")


class IssueNoteRecord(Base):
    __tablename__ = "issue_notes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    issue_id: Mapped[str] = mapped_column(
        String, ForeignKey("issues.id"), nullable=False
    )
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    issue: Mapped[IssueRecord] = relationship("IssueRecord", back_populates="notes")


class MonitoringStateModel(Base):
    __tablename__ = "monitoring_state"

    asset_id: Mapped[str] = mapped_column(String, primary_key=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    freshness_status: Mapped[str | None] = mapped_column(String, nullable=True)
    last_schema_hash: Mapped[str] = mapped_column(String, default="")
    last_owner: Mapped[str | None] = mapped_column(String, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
