"""The GraphError-degradation contract: a URN the live DataHub doesn't know must
yield a graceful miss (None/empty), not a 500. Genuine errors still propagate.
"""

import pytest

from app.integrations.datahub_graph import DataHubGraphClient

# The degradation path catches the SDK's GraphError; skip where the SDK (only
# needed for a live DataHub) isn't installed, e.g. CI. Runs locally with it.
GraphError = pytest.importorskip("datahub.configuration.common").GraphError

_NOT_FOUND = (
    "Error executing graphql query: Failed to find entity "
    "with name x in EntityRegistry"
)


class _RaisingGraph:
    def __init__(self, message):
        self._message = message

    def execute_graphql(self, *args, **kwargs):
        raise GraphError(self._message)


def _client(monkeypatch, message):
    client = DataHubGraphClient(server="http://localhost:8080")
    monkeypatch.setattr(client, "_graph", lambda: _RaisingGraph(message))
    return client


def test_get_asset_degrades_to_none(monkeypatch):
    client = _client(monkeypatch, _NOT_FOUND)
    assert client.get_asset("urn:li:dataset:x") is None


def test_get_lineage_degrades_to_empty(monkeypatch):
    client = _client(monkeypatch, _NOT_FOUND)
    lineage = client.get_lineage("urn:li:dataset:x")
    assert lineage.upstream == []
    assert lineage.downstream == []


def test_search_degrades_to_empty(monkeypatch):
    client = _client(monkeypatch, _NOT_FOUND)
    assert client.search("anything") == []


def test_genuine_error_reraises(monkeypatch):
    client = _client(monkeypatch, "Unexpected server explosion")
    with pytest.raises(GraphError):
        client.get_asset("urn:li:dataset:x")
