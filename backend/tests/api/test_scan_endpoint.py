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
