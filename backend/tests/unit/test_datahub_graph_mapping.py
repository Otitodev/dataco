"""Exercise DataHubGraphClient's GraphQL -> domain mapping offline.

We inject a stub graph whose ``execute_graphql`` returns canned responses, so
the parsing/mapping logic is verified without the acryl-datahub SDK or a live
DataHub instance.
"""

from app.domain.types import Field
from app.integrations.datahub_graph import (
    DataHubGraphClient,
    _is_transient_report_error,
)


def test_transient_report_errors_trigger_retry():
    # Eventual-consistency / OpenSearch-warmup wordings must all be retryable.
    for msg in (
        "Assertion urn:li:assertion:x does not exist",
        "Failed to retrieve entity for assertion with urn ...",
        "Search query failed:. search",
        "search: Try again",
    ):
        assert _is_transient_report_error(Exception(msg)), msg


def test_non_transient_report_error_surfaces_immediately():
    assert not _is_transient_report_error(Exception("Unauthorized: invalid token"))
    assert not _is_transient_report_error(Exception("Unknown type Foo"))

URN = "urn:li:dataset:(urn:li:dataPlatform:snowflake,DB.PUBLIC.lab_ingestion_feed,PROD)"

_ASSET = {
    "dataset": {
        "urn": URN,
        "name": "lab_ingestion_feed",
        "properties": {"name": "lab_ingestion_feed", "description": "Lab results feed"},
        "editableProperties": {"description": None},
        "ownership": {"owners": [{"owner": {"urn": "urn:li:corpGroup:lab-team"}}]},
        "schemaMetadata": {
            "fields": [
                {"fieldPath": "patient_id", "nativeDataType": "int"},
                {"fieldPath": "result_value", "nativeDataType": "float"},
            ]
        },
        "tags": {"tags": [{"tag": {"urn": "urn:li:tag:pii"}}]},
    }
}

_LINEAGE = {
    "dataset": {
        "upstream": {
            "relationships": [
                {"entity": {"urn": "urn:li:dataset:lims", "name": "lims_export"}}
            ]
        },
        "downstream": {
            "relationships": [
                {
                    "entity": {
                        "urn": "urn:li:dataset:d1",
                        "properties": {"name": "malaria_positivity_dashboard"},
                    }
                }
            ]
        },
    }
}

_SEARCH = {
    "search": {
        "searchResults": [
            {
                "entity": {
                    "urn": URN,
                    "properties": {"name": "lab_ingestion_feed"},
                    "ownership": {
                        "owners": [{"owner": {"urn": "urn:li:corpuser:jdoe"}}]
                    },
                }
            }
        ]
    }
}


class _StubGraph:
    def __init__(self, response):
        self._response = response

    def execute_graphql(self, query, variables=None):
        return self._response


def _client(response) -> DataHubGraphClient:
    c = DataHubGraphClient(server="http://localhost:8080", token="x")
    c._graph_client = _StubGraph(response)  # bypass the lazy SDK build
    return c


def test_get_asset_maps_all_fields():
    asset = _client(_ASSET).get_asset(URN)
    assert asset is not None
    assert asset.name == "lab_ingestion_feed"
    assert asset.description == "Lab results feed"
    assert asset.owner == "lab-team"  # corpGroup urn -> readable id
    assert asset.schema_fields == [
        Field("patient_id", "int"),
        Field("result_value", "float"),
    ]
    assert asset.tags == ["pii"]  # tag urn -> readable id


def test_get_asset_returns_none_when_dataset_missing():
    assert _client({"dataset": None}).get_asset(URN) is None


def test_get_assets_batches_and_maps_present_only():
    # Aliased batch response: a0 resolves, a1 (missing asset) is null.
    resp = {"a0": _ASSET["dataset"], "a1": None}
    result = _client(resp).get_assets([URN, "urn:li:dataset:missing"])
    assert set(result) == {URN}
    assert result[URN].name == "lab_ingestion_feed"


def test_get_assets_empty_input_makes_no_request():
    # Empty list short-circuits without touching the graph client.
    assert DataHubGraphClient("http://x", "t").get_assets([]) == {}


def test_get_lineage_maps_upstream_and_downstream():
    lineage = _client(_LINEAGE).get_lineage(URN)
    assert [n.name for n in lineage.upstream] == ["lims_export"]
    assert [n.name for n in lineage.downstream] == ["malaria_positivity_dashboard"]


def test_search_maps_results():
    results = _client(_SEARCH).search("lab")
    assert len(results) == 1
    assert results[0].name == "lab_ingestion_feed"
    assert results[0].owner == "jdoe"  # corpuser urn -> readable id


def test_parsing_is_defensive_on_empty_shapes():
    # Missing nested keys must degrade to empty/None, never raise.
    asset = _client({"dataset": {"urn": URN}}).get_asset(URN)
    assert asset is not None
    assert asset.owner is None
    assert asset.schema_fields == []
    assert asset.tags == []
    lineage = _client({"dataset": {}}).get_lineage(URN)
    assert lineage.upstream == [] and lineage.downstream == []


def test_lineage_names_non_dataset_entities():
    # Dashboards/charts resolve via info.name; dataJobs fall back to the
    # jobId segment of their URN (validated against live DataHub 1.6.x).
    response = {
        "dataset": {
            "upstream": {
                "relationships": [
                    {
                        "entity": {
                            "urn": (
                                "urn:li:dataJob:(urn:li:dataFlow:(spark,"
                                "b2fd91.export_table_orders_to_s3,b2fd91.default),"
                                "b2fd91.export_table_orders_to_s3)"
                            ),
                            "jobId": "b2fd91.export_table_orders_to_s3",
                        }
                    }
                ]
            },
            "downstream": {
                "relationships": [
                    {
                        "entity": {
                            "urn": "urn:li:dashboard:(looker,b2fd91.dashboards.53)",
                            "info": {"name": "Order Overview"},
                        }
                    }
                ]
            },
        }
    }
    lineage = _client(response).get_lineage(URN)
    assert [n.name for n in lineage.upstream] == ["export_table_orders_to_s3"]
    assert [n.name for n in lineage.downstream] == ["Order Overview"]
