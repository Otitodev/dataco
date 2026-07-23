from datetime import UTC, datetime

from app.repository.models import IssueRecord, MonitoringStateModel


def build_issue(
    *,
    asset_id: str = "urn:default",
    asset_name: str = "default_dataset",
    issue_type: str = "schema_drift",
    severity: str = "high",
    status: str = "active",
    owner: str | None = "lab-team",
    blast_radius: int = 0,
    impacted_assets: list[str] | None = None,
    created_at: datetime | None = None,
) -> IssueRecord:
    issue = IssueRecord(
        asset_id=asset_id,
        asset_name=asset_name,
        issue_type=issue_type,
        severity=severity,
        status=status,
        owner=owner,
        blast_radius=blast_radius,
        created_at=created_at or datetime.now(UTC),
    )
    if impacted_assets:
        issue.set_impacted(impacted_assets)
    return issue


def build_monitoring_state(
    *,
    asset_id: str = "urn:default",
    schema_hash: str = "",
    owner: str | None = None,
    last_checked: datetime | None = None,
) -> MonitoringStateModel:
    return MonitoringStateModel(
        asset_id=asset_id,
        last_schema_hash=schema_hash,
        last_owner=owner,
        last_checked_at=last_checked or datetime.now(UTC),
    )


DEMO_ASSETS = [
    {
        "asset_id": "urn:dataco:lab_ingestion_feed",
        "asset_name": "lab_ingestion_feed",
        "issue_type": "schema_drift",
        "severity": "critical",
        "owner": "lab-team",
        "blast_radius": 4,
        "impacted": [
            "malaria_positivity_dashboard",
            "lab_turnaround_report",
            "specimen_tracking_dashboard",
            "quality_metrics_report",
        ],
    },
    {
        "asset_id": "urn:dataco:patient_registry",
        "asset_name": "patient_registry",
        "issue_type": "freshness_stale",
        "severity": "high",
        "owner": None,
        "blast_radius": 3,
        "impacted": [
            "patient_cohort_analysis",
            "clinical_trial_matching",
            "demographics_report",
        ],
    },
    {
        "asset_id": "urn:dataco:claims_ingestion",
        "asset_name": "claims_ingestion",
        "issue_type": "owner_changed",
        "severity": "medium",
        "owner": "billing-team",
        "blast_radius": 2,
        "impacted": [
            "revenue_cycle_dashboard",
            "denial_rate_report",
        ],
    },
]
