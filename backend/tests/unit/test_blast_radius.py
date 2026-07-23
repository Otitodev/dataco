from app.domain.blast_radius import blast_radius, critical_path
from app.domain.types import AssetNode, Lineage


def _make_node(urn: str, name: str = "") -> AssetNode:
    return AssetNode(urn=urn, name=name or urn)


def test_blast_radius_returns_downstream():
    lineage = Lineage(
        upstream=[_make_node("urn:source")],
        downstream=[
            _make_node("urn:dash_1", "Dashboard A"),
            _make_node("urn:dash_2", "Dashboard B"),
            _make_node("urn:dash_3", "Dashboard C"),
        ],
    )
    result = blast_radius(lineage)
    assert len(result) == 3
    assert result[0].name == "Dashboard A"


def test_blast_radius_empty_when_no_downstream():
    lineage = Lineage(upstream=[_make_node("urn:src")], downstream=[])
    assert blast_radius(lineage) == []


def test_critical_path_returns_downstream_nodes():
    lineage = Lineage(
        downstream=[
            _make_node("urn:a"),
            _make_node("urn:b"),
            _make_node("urn:c"),
        ]
    )
    path = critical_path(lineage)
    assert len(path) > 0


def test_critical_path_empty_when_no_downstream():
    lineage = Lineage()
    assert critical_path(lineage) == []
