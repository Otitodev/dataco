from datetime import datetime, timedelta

from app.domain.detection import check_asset
from app.domain.schema_diff import schema_hash
from app.domain.types import AssetMeta, Field, IssueType, MonitoringState

T0 = datetime(2026, 7, 1, 10, 0, 0)


def _meta(schema_fields=None, owner="lab-team", urn="urn:lab_feed", name="lab_feed"):
    return AssetMeta(
        urn=urn,
        name=name,
        schema_fields=(
            schema_fields or [Field("patient_id", "int"), Field("result", "str")]
        ),
        owner=owner,
    )


def _state(schema_hash_val="abc", owner="lab-team", last_checked=None):
    return MonitoringState(
        asset_id="urn:lab_feed",
        last_schema_hash=schema_hash_val,
        last_owner=owner,
        last_checked_at=last_checked or T0,
    )


def test_check_asset_flags_schema_drift():
    prev = _state(schema_hash_val="abc")
    current = _meta(
        schema_fields=[Field("patient_id", "int"), Field("result", "float")]
    )

    issue = check_asset(prev, current, now=lambda: T0 + timedelta(hours=1))
    assert issue is not None
    assert issue["issue_type"] == IssueType.SCHEMA_DRIFT


def test_check_asset_returns_none_when_unchanged():
    fields = [Field("patient_id", "int"), Field("result", "str")]
    h = schema_hash(fields)
    prev = _state(schema_hash_val=h)
    current = _meta(schema_fields=fields)

    assert check_asset(prev, current, now=lambda: T0) is None


def test_check_asset_flags_owner_changed():
    fields = [Field("patient_id", "int"), Field("result", "str")]
    h = schema_hash(fields)
    prev = _state(schema_hash_val=h, owner="old-team")
    current = _meta(schema_fields=fields, owner="new-team")

    issue = check_asset(prev, current, now=lambda: T0 + timedelta(hours=1))
    assert issue is not None
    assert issue["issue_type"] == IssueType.OWNER_CHANGED


def test_check_asset_flags_owner_missing():
    fields = [Field("patient_id", "int"), Field("result", "str")]
    h = schema_hash(fields)
    prev = _state(schema_hash_val=h, owner="lab-team")
    current = _meta(schema_fields=fields, owner=None)

    issue = check_asset(prev, current, now=lambda: T0 + timedelta(hours=1))
    assert issue is not None
    assert issue["issue_type"] == IssueType.OWNER_MISSING


def test_check_asset_flags_freshness_stale():
    prev = _state(schema_hash_val=schema_hash([Field("id", "int")]))
    current = _meta(schema_fields=[Field("id", "int")])

    issue = check_asset(prev, current, now=lambda: T0 + timedelta(hours=25))
    assert issue is not None
    assert issue["issue_type"] == IssueType.FRESHNESS_STALE


def test_check_asset_returns_none_when_recent():
    fields = [Field("id", "int")]
    h = schema_hash(fields)
    prev = _state(schema_hash_val=h, last_checked=T0)
    current = _meta(schema_fields=fields)

    assert check_asset(prev, current, now=lambda: T0 + timedelta(hours=1)) is None
