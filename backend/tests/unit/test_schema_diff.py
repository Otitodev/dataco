from app.domain.schema_diff import diff_schema, schema_hash
from app.domain.types import Field


def test_reordering_fields_is_not_drift():
    before = [Field("a", "int"), Field("b", "str")]
    after = [Field("b", "str"), Field("a", "int")]
    assert schema_hash(before) == schema_hash(after)


def test_type_change_is_detected():
    diff = diff_schema(
        before=[Field("patient_id", "int")],
        after=[Field("patient_id", "str")],
    )
    assert diff.type_changed == [("patient_id", "int", "str")]
    assert diff.has_drift


def test_field_added_is_detected():
    diff = diff_schema(
        before=[Field("id", "int")],
        after=[Field("id", "int"), Field("name", "str")],
    )
    assert diff.added == ["name"]
    assert diff.has_drift


def test_field_removed_is_detected():
    diff = diff_schema(
        before=[Field("id", "int"), Field("name", "str")],
        after=[Field("id", "int")],
    )
    assert diff.removed == ["name"]
    assert diff.has_drift


def test_no_change_returns_empty_diff():
    fields = [Field("id", "int"), Field("name", "str")]
    diff = diff_schema(before=fields, after=fields)
    assert not diff.has_drift
    assert diff.added == []
    assert diff.removed == []
    assert diff.type_changed == []


def test_schema_hash_is_stable():
    fields = [Field("patient_id", "int"), Field("name", "str")]
    assert schema_hash(fields) == schema_hash(fields)


def test_empty_fields_hash_is_empty():
    assert schema_hash([]) == schema_hash([])
