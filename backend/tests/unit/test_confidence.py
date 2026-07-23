
from app.domain.confidence import ConfidenceContext, confidence_label


def test_high_confidence_when_owner_and_lineage_present():
    ctx = ConfidenceContext(owner_present=True, lineage_complete=True)
    assert confidence_label(ctx) == "high"


def test_medium_confidence_when_only_owner_present():
    ctx = ConfidenceContext(owner_present=True, lineage_complete=False)
    assert confidence_label(ctx) == "medium"


def test_medium_confidence_when_only_lineage_present():
    ctx = ConfidenceContext(owner_present=False, lineage_complete=True)
    assert confidence_label(ctx) == "medium"


def test_low_confidence_when_both_missing():
    ctx = ConfidenceContext(owner_present=False, lineage_complete=False)
    assert confidence_label(ctx) == "low"
