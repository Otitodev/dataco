def test_dashboard_returns_active_issues(client):
    res = client.get("/dashboard")
    assert res.status_code == 200
    issues = res.json()
    assert len(issues) == 3
    assert issues[0]["severity"] == "critical"
    assert issues[0]["blast_radius"] == 4


def test_issue_detail_returns_full_issue(client):
    res = client.get("/dashboard")
    issue_id = res.json()[0]["id"]

    res = client.get(f"/issue/{issue_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == issue_id
    assert data["asset_name"] == "lab_ingestion_feed"
    assert data["severity"] == "critical"
    # Write-back provenance is exposed (null until an issue is written back).
    assert "datahub_tag_urn" in data
    assert "datahub_assertion_urn" in data
    assert "written_back_at" in data


def test_issue_not_found_returns_404(client):
    res = client.get("/issue/nonexistent")
    assert res.status_code == 404
