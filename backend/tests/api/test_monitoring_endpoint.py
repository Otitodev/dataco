"""API tests for the monitoring (watchlist) endpoints.

Uses the offline ``FakeDataHubClient`` (DEMO_DATA has ``lab_ingestion_feed``),
so add resolves a real asset and a bad URN 404s.
"""

FEED = "urn:dataco:lab_ingestion_feed"


def test_add_list_remove_monitored(client):
    # Add a known asset -> baseline primed, returned with its name.
    resp = client.post("/monitored", json={"urn": FEED})
    assert resp.status_code == 200
    body = resp.json()
    assert body["urn"] == FEED
    assert body["name"] == "lab_ingestion_feed"

    # It now appears in the watchlist...
    listed = client.get("/monitored").json()
    assert any(a["urn"] == FEED for a in listed)

    # ...and the scan status watch_count reflects it.
    assert client.get("/scan/status").json()["watch_count"] >= 1

    # Remove it -> gone.
    rm = client.delete("/monitored", params={"urn": FEED})
    assert rm.status_code == 200
    assert all(a["urn"] != FEED for a in client.get("/monitored").json())


def test_add_unknown_asset_404s(client):
    resp = client.post("/monitored", json={"urn": "urn:dataco:does_not_exist"})
    assert resp.status_code == 404


def test_remove_unmonitored_404s(client):
    resp = client.delete("/monitored", params={"urn": "urn:dataco:never_added"})
    assert resp.status_code == 404
