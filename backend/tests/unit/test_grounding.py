from app.domain.grounding import ground_assets


def test_keeps_only_assets_in_context():
    allowed = ["malaria_positivity_dashboard", "lab_turnaround_report"]
    candidates = ["malaria_positivity_dashboard", "totally_made_up_asset"]
    assert ground_assets(candidates, allowed) == ["malaria_positivity_dashboard"]


def test_is_case_and_whitespace_insensitive():
    allowed = ["Malaria_Positivity_Dashboard"]
    assert ground_assets(["  malaria_positivity_dashboard  "], allowed) == [
        "  malaria_positivity_dashboard  "  # original preserved, matched normalized
    ]


def test_preserves_order_and_dedupes():
    allowed = ["a", "b", "c"]
    assert ground_assets(["c", "a", "a", "c"], allowed) == ["c", "a"]


def test_drops_blank_and_unknown():
    assert ground_assets(["", "  ", "ghost"], ["real"]) == []


def test_empty_inputs():
    assert ground_assets([], ["a"]) == []
    assert ground_assets(["a"], []) == []
