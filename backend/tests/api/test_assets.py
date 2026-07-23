def test_get_asset_returns_metadata(client):
    res = client.get("/asset/urn:dataco:lab_ingestion_feed")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "lab_ingestion_feed"
    assert data["owner"] == "lab-team"
    assert len(data["schema_fields"]) == 4


def test_get_lineage_returns_upstream_downstream(client):
    res = client.get("/lineage/urn:dataco:lab_ingestion_feed")
    assert res.status_code == 200
    data = res.json()
    assert len(data["upstream"]) == 1
    assert len(data["downstream"]) == 4
    assert data["downstream"][0]["name"] == "malaria_positivity_dashboard"


def test_search_returns_matching_assets(client):
    res = client.get("/search?q=lab")
    assert res.status_code == 200
    results = res.json()
    assert len(results) >= 1
    assert results[0]["name"] == "lab_ingestion_feed"
