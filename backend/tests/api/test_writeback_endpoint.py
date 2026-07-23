def test_writeback_endpoint(client, seeded_repo):
    issue = seeded_repo.list_active_issues()[0]

    resp = client.post(f"/issue/{issue.id}/writeback")

    assert resp.status_code == 200
    body = resp.json()
    assert body["issue_id"] == issue.id
    assert body["ok"] is True
    assert body["tag_urn"].startswith("urn:li:tag:")
    assert body["assertion_urn"].startswith("urn:li:assertion:")


def test_writeback_unknown_issue_404(client):
    resp = client.post("/issue/does-not-exist/writeback")
    assert resp.status_code == 404
