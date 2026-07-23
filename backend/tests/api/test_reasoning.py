def test_explain_returns_summary(client):
    res = client.get("/dashboard")
    issue_id = res.json()[0]["id"]

    res = client.post("/explain", json={"issue_id": issue_id})
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data
    assert "likely_cause" in data
    assert data["confidence"] in ("high", "medium", "low")


def test_explain_persists_to_issue(client):
    issue_id = client.get("/dashboard").json()[0]["id"]

    # Before: seeded issues have no explanation yet.
    before = client.get(f"/issue/{issue_id}").json()
    assert before["summary"] is None
    assert before["confidence"] is None

    client.post("/explain", json={"issue_id": issue_id})

    # After: the explanation is durable on the issue record.
    after = client.get(f"/issue/{issue_id}").json()
    assert after["summary"]
    assert after["confidence"] in ("high", "medium", "low")


def test_explain_unknown_issue_404s(client):
    res = client.post("/explain", json={"issue_id": "does-not-exist"})
    assert res.status_code == 404


def test_confidence_is_rule_based(client):
    issues = client.get("/dashboard").json()
    # Critical issue = lab_ingestion_feed: has owner + 4 downstream in the fake
    # DataHub -> rule says HIGH, regardless of what the model self-reports.
    lab = issues[0]
    assert (
        client.post("/explain", json={"issue_id": lab["id"]}).json()["confidence"]
        == "high"
    )

    # patient_registry: no owner, no lineage in the fake -> rule says LOW.
    registry = next(i for i in issues if i["asset_name"] == "patient_registry")
    assert (
        client.post("/explain", json={"issue_id": registry["id"]}).json()["confidence"]
        == "low"
    )


def test_grounding_guard_strips_hallucinated_assets(seeded_repo, db_session):
    from fastapi.testclient import TestClient

    from app.deps import get_datahub, get_db, get_llm, get_repo
    from app.integrations.llm import Explanation
    from app.main import create_app
    from tests.fakes import DEMO_DATA, FakeDataHubClient, StubLLMClient

    # A model that references a real downstream asset AND an invented one.
    hallucinating = StubLLMClient(
        explanation=Explanation(
            summary="Schema drift.",
            likely_cause="Type change.",
            impacted_assets=["malaria_positivity_dashboard", "totally_made_up_asset"],
            confidence="high",
            recommended_action="Fix it.",
        )
    )

    app = create_app()
    app.dependency_overrides[get_datahub] = lambda: FakeDataHubClient(**DEMO_DATA)
    app.dependency_overrides[get_llm] = lambda: hallucinating
    app.dependency_overrides[get_db] = lambda: iter([db_session])
    app.dependency_overrides[get_repo] = lambda: seeded_repo
    guard_client = TestClient(app)

    lab_id = guard_client.get("/dashboard").json()[0]["id"]
    impacted = (
        guard_client.post("/explain", json={"issue_id": lab_id})
        .json()["impacted_assets"]
    )

    assert "malaria_positivity_dashboard" in impacted  # grounded -> kept
    assert "totally_made_up_asset" not in impacted  # ungrounded -> stripped


def test_brief_returns_structured_brief(client):
    res = client.get("/dashboard")
    issue_id = res.json()[0]["id"]

    res = client.post("/brief", json={"issue_id": issue_id})
    assert res.status_code == 200
    data = res.json()
    assert "subject" in data
    assert "what_happened" in data
    assert len(data["what_is_affected"]) > 0
    assert "estimated_impact" in data
