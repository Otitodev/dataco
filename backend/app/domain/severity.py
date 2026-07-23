from app.domain.types import IssueType, Severity

SEVERITY_ORDER: dict[Severity, int] = {
    Severity.LOW: 0,
    Severity.MEDIUM: 1,
    Severity.HIGH: 2,
    Severity.CRITICAL: 3,
}


def compute_severity(
    issue_type: IssueType, blast_radius: int, stale_hours: float
) -> Severity:
    if blast_radius >= 4 or stale_hours >= 24:
        return Severity.CRITICAL
    if blast_radius >= 3 or stale_hours >= 12:
        return Severity.HIGH
    if blast_radius >= 2 or stale_hours >= 6:
        return Severity.MEDIUM
    return Severity.LOW
