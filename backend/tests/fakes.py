from app.domain.types import AssetMeta, AssetNode, Field, Lineage
from app.integrations.llm import Brief, Explanation


class FakeDataHubClient:
    def __init__(self, assets=None, lineage=None, hits=None):
        self._assets = assets or {}
        self._lineage = lineage or {}
        self._hits = hits or []
        # Records write-back calls so the offline/test path is demonstrable
        # without a live DataHub. Each entry: (kind, urn, payload).
        self.writes: list[tuple] = []

    def search(self, query: str) -> list[AssetMeta]:
        return self._hits

    def get_asset(self, urn: str) -> AssetMeta | None:
        return self._assets.get(urn)

    def get_assets(self, urns: list[str]) -> dict[str, AssetMeta]:
        return {u: self._assets[u] for u in urns if u in self._assets}

    def get_lineage(self, urn: str) -> Lineage:
        return self._lineage.get(urn, Lineage())

    def tag_asset(self, urn: str, tag: str) -> str | None:
        tag_urn = f"urn:li:tag:{tag}"
        self.writes.append(("tag", urn, tag_urn))
        return tag_urn

    def assert_issue(
        self,
        urn: str,
        *,
        issue_type: str,
        severity: str,
        description: str,
        field_path: str | None = None,
    ) -> str | None:
        self.writes.append(
            ("assertion", urn, {"issue_type": issue_type, "severity": severity})
        )
        return f"urn:li:assertion:dataco-{issue_type}"


class StubLLMClient:
    def __init__(self, explanation=None, brief=None):
        self._explanation = explanation or Explanation(
            summary="Schema drift detected in lab_ingestion_feed.",
            likely_cause="The patient_id column type changed from int to str.",
            impacted_assets=["malaria_positivity_dashboard"],
            confidence="high",
            recommended_action="Contact lab-team to update the ETL mapping.",
        )
        self._brief = brief or Brief(
            subject="Lab Ingestion Feed Schema Change",
            what_happened=(
                "The lab_ingestion_feed dataset had a schema change. "
                "The patient_id column type was changed from int to str, "
                "breaking the ETL pipeline for downstream dashboards."
            ),
            what_is_affected=["malaria_positivity_dashboard", "lab_turnaround_report"],
            who_to_contact="lab-team (Data Engineering)",
            next_step=(
                "Update the ETL mapping to accept the new column type, "
                "or revert the schema change."
            ),
            estimated_impact="high",
        )

    def explain(self, context: dict) -> Explanation:
        return self._explanation

    def brief(self, context: dict) -> Brief:
        return self._brief


DEMO_DATA = {
    "assets": {
        "urn:dataco:lab_ingestion_feed": AssetMeta(
            urn="urn:dataco:lab_ingestion_feed",
            name="lab_ingestion_feed",
            description="Lab results ingestion feed for hospital information system",
            owner="lab-team",
            schema_fields=[
                Field("patient_id", "int"),
                Field("test_code", "str"),
                Field("result_value", "float"),
                Field("timestamp", "datetime"),
            ],
            freshness="2 hours ago",
            tags=["healthcare", "lab", "pii"],
        ),
    },
    "lineage": {
        "urn:dataco:lab_ingestion_feed": Lineage(
            upstream=[AssetNode(urn="urn:dataco:lims_export", name="lims_export")],
            downstream=[
                AssetNode(urn="urn:dataco:dash_1", name="malaria_positivity_dashboard"),
                AssetNode(urn="urn:dataco:dash_2", name="lab_turnaround_report"),
                AssetNode(urn="urn:dataco:dash_3", name="specimen_tracking_dashboard"),
                AssetNode(urn="urn:dataco:dash_4", name="quality_metrics_report"),
            ],
        ),
    },
    "hits": [
        AssetMeta(
            urn="urn:dataco:lab_ingestion_feed",
            name="lab_ingestion_feed",
            owner="lab-team",
        ),
    ],
}
