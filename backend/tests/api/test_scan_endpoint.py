def test_scan_endpoint_returns_results(client):
    resp = client.post("/scan", json={"urns": ["urn:dataco:lab_ingestion_feed"]})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list) and len(body) == 1
    assert body[0]["urn"] == "urn:dataco:lab_ingestion_feed"
    assert "detected" in body[0]


def test_scan_endpoint_defaults_to_watchlist(client):
    # No urns and no primed monitoring state -> falls back to the WATCHLIST.
    resp = client.post("/scan", json={})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_scan_status_disabled_by_default(client):
    # The scheduler is opt-in (SCAN_INTERVAL_SECONDS=0), so tests never start a
    # loop; status must report disabled with a non-empty watchlist.
    resp = client.get("/scan/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is False
    assert body["interval_seconds"] == 0
    assert body["last_run_at"] is None
    assert body["watch_count"] >= 1
