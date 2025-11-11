from pathlib import Path

from fastapi.testclient import TestClient

from server.run_dev_server import app, GRAPH, SKILLS

client = TestClient(app)


def seed_skill(tmp_path):
    SKILLS.path = tmp_path / "skills.json"
    SKILLS.skills = {}
    GRAPH.skills["skill-1"] = {"id": "skill-1", "content": {"text": "Test skill"}, "references": 3}
    SKILLS.sync(GRAPH.get_skills())


def test_skill_listing_and_sharing(tmp_path):
    seed_skill(tmp_path)
    client.post(
        "/governance/consent",
        json={"tenant": "demo", "project": "demo", "user": "sess-xyz", "consent": True},
    )
    resp = client.get("/skills", params={"session_id": "sess-xyz"})
    data = resp.json()
    assert data["skills"]

    share = client.post("/skills/share", json={"skill_id": "skill-1", "cohort": "team-alpha"})
    assert share.json()["ok"]
    listing = client.get("/skills", params={"session_id": "sess-xyz", "cohort": "team-alpha"}).json()
    assert listing["skills"]
