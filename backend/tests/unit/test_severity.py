import pytest

from app.domain.severity import compute_severity
from app.domain.types import IssueType, Severity


@pytest.mark.parametrize(
    "blast,hours,expected",
    [
        (0, 0, Severity.LOW),
        (1, 1, Severity.LOW),
        (2, 6, Severity.MEDIUM),
        (2, 0, Severity.MEDIUM),
        (1, 7, Severity.MEDIUM),
        (3, 12, Severity.HIGH),
        (3, 0, Severity.HIGH),
        (1, 13, Severity.HIGH),
        (4, 0, Severity.CRITICAL),
        (0, 24, Severity.CRITICAL),
        (5, 30, Severity.CRITICAL),
    ],
)
def test_severity_matrix(blast, hours, expected):
    assert compute_severity(IssueType.FRESHNESS_STALE, blast, hours) == expected


def test_critical_when_blast_radius_reaches_four():
    result = compute_severity(IssueType.SCHEMA_DRIFT, blast_radius=4, stale_hours=0)
    assert result is Severity.CRITICAL


def test_critical_when_stale_for_24_hours():
    result = compute_severity(IssueType.FRESHNESS_STALE, blast_radius=1, stale_hours=24)
    assert result is Severity.CRITICAL


def test_low_when_single_downstream_and_recent():
    result = compute_severity(IssueType.OWNER_CHANGED, blast_radius=1, stale_hours=1)
    assert result is Severity.LOW
