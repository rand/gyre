from fastapi.testclient import TestClient

from server.run_dev_server import app, PRIVATE

client = TestClient(app)


def seed_session():
    PRIVATE.items.clear()
    resp = client.post(
        "/observe/ingest",
        json={
            "session_id": "sess-123",
            "events": [
                {"kind": "user", "payload": {"text": "Need DenverSuspension plan"}},
                {"kind": "agent", "payload": {"text": "Draft plan"}},
            ],
        },
    )
    assert resp.status_code == 200


def test_ingest_and_propose_flow():
    seed_session()
    body = client.get("/review/candidates", params={"session_id": "sess-123"}).json()
    assert body["candidates"]

    propose = client.post(
        "/patches/propose",
        json={
            "session_id": "sess-123",
            "task_desc": "Need DenverSuspension plan",
            "budgets": {"tokens": 500, "latency_ms": 200},
            "slot_specs": [{"name": "task_header", "max_tokens": 100}, {"name": "retrieved_evidence", "max_tokens": 200}],
        },
    )
    pdata = propose.json()
    assert pdata["patches"]
    assert pdata["stage_a"]["executed"]
    assert pdata["ledger"]["tokens_used"] <= 500
    assert pdata["trace"]


def test_manual_export_uses_session_candidates():
    seed_session()
    candidates_resp = client.get("/review/candidates", params={"session_id": "sess-123"}).json()
    candidates = candidates_resp["candidates"]
    patch = client.post(
        "/review/export_patch",
        json={
            "session_id": "sess-123",
            "candidate_ids": [candidates[0]["id"]],
            "slot_specs": [{"name": "task_header", "max_tokens": 100}, {"name": "retrieved_evidence", "max_tokens": 200}],
            "note": "manual patch",
        },
    ).json()
    assert patch["patch"]["id"].startswith("manual-")
    audit = client.get("/review/audit").json()
    assert audit["audit_log"]


def test_metrics_endpoint_tracks_ingest():
    seed_session()
    metrics = client.get("/metrics/observer").json()
    assert metrics["totals"]["ingest_calls"] >= 1
    assert metrics["latest_observe"]["session_id"] == "sess-123"


def test_inject_endpoint_returns_ack():
    seed_session()
    client.post("/governance/consent", json={"tenant": "demo", "project": "demo", "user": "sess-123", "consent": False})
    propose = client.post(
        "/patches/propose",
        json={
            "session_id": "sess-123",
            "task_desc": "Need DenverSuspension plan",
            "budgets": {"tokens": 500, "latency_ms": 200},
            "slot_specs": [{"name": "task_header", "max_tokens": 100}],
        },
    ).json()
    patch = propose["patches"][0]
    # missing consent
    resp = client.post("/patches/inject", json={"patch": patch, "transport": "openai"})
    assert resp.status_code == 403
    client.post("/governance/consent", json={"tenant": "demo", "project": "demo", "user": "sess-123", "consent": True})
    resp = client.post("/patches/inject", json={"patch": patch, "transport": "openai"})
    data = resp.json()
    assert data["ok"]
    assert data["transport"] == "openai"
    client.post("/transports/chaos", json={"transport": "openai", "available": False})
    status = client.get("/transports/status").json()
    assert status["transports"]["openai"] is False
