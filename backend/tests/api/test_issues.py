def test_update_issue_status(client):
    res = client.get("/dashboard")
    issue_id = res.json()[0]["id"]

    res = client.patch(f"/issue/{issue_id}", json={"status": "investigating"})
    assert res.status_code == 200
    assert res.json()["status"] == "investigating"


def test_add_and_list_notes(client):
    res = client.get("/dashboard")
    issue_id = res.json()[0]["id"]

    res = client.post(
        f"/issue/{issue_id}/note",
        json={"note_text": "Checking upstream", "author": "Ana"},
    )
    assert res.status_code == 200
    note = res.json()
    assert note["note_text"] == "Checking upstream"

    res = client.get(f"/issue/{issue_id}/notes")
    assert res.status_code == 200
    notes = res.json()
    assert len(notes) == 1
    assert notes[0]["author"] == "Ana"


def test_resolve_issue_sets_resolved_at(client):
    res = client.get("/dashboard")
    issue_id = res.json()[0]["id"]

    res = client.patch(f"/issue/{issue_id}", json={"status": "resolved"})
    assert res.status_code == 200
    assert res.json()["resolved_at"] is not None
