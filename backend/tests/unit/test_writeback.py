from app.integrations.datahub_graph import _assertion_id, _assertion_severity
from app.repository.models import IssueRecord
from app.services.writeback import _tag_for, write_back_issue
from tests.fakes import FakeDataHubClient


def test_tag_for_namespacing():
    assert _tag_for("schema_drift") == "trust:schema_drift"


def test_assertion_id_deterministic_and_scoped():
    a = _assertion_id("urn:li:dataset:x", "schema_drift")
    assert a == _assertion_id("urn:li:dataset:x", "schema_drift")  # stable
    assert a != _assertion_id("urn:li:dataset:x", "freshness_stale")  # by type
    assert a != _assertion_id("urn:li:dataset:y", "schema_drift")  # by asset
    assert a.startswith("dataco-")


def test_assertion_severity_mapping():
    assert _assertion_severity("critical") == "HIGH"
    assert _assertion_severity("high") == "HIGH"
    assert _assertion_severity("medium") == "MEDIUM"
    assert _assertion_severity("low") == "LOW"
    assert _assertion_severity("") == "LOW"


def test_write_back_issue_records_tag_and_assertion():
    issue = IssueRecord(
        asset_id="urn:dataco:x",
        asset_name="x",
        issue_type="schema_drift",
        severity="critical",
    )
    dh = FakeDataHubClient()
    result = write_back_issue(dh, issue)

    assert result.ok
    assert result.tag_urn == "urn:li:tag:trust:schema_drift"
    assert result.assertion_urn.startswith("urn:li:assertion:")
    kinds = [w[0] for w in dh.writes]
    assert "tag" in kinds and "assertion" in kinds
