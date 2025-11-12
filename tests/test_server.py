from fastapi.testclient import TestClient

from server.run_dev_server import app, PRIVATE, FEEDBACK, PILOT
from gyre.feedback import FeedbackStore
from gyre.pilot import PilotRollout

client = TestClient(app)


def seed_session():
    PRIVATE.items.clear()
    client.post(
        "/sessions/register",
        json={"session_id": "sess-123", "tenant": "demo", "project": "demo", "user": "sess-123"},
    )
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
    assert pdata["stage_a"]["executed_plan_ids"]
    assert pdata["stage_a"]["plans"]
    assert pdata["patches"][0]["body_unredacted"]
    assert pdata["ledger"]["tokens_used"] <= 500
    assert pdata["trace"]
    assert pdata["scope"]["tenant"] == "demo"
    assert pdata["scope"]["project"] == "demo"


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


def test_feature_flags_and_dspy_metrics(tmp_path):
    from server.run_dev_server import DATA_LOGGER, FLAGS

    DATA_LOGGER.path = tmp_path / "propose.jsonl"
    FLAGS.set("dspy_logging", True)
    seed_session()
    client.post(
        "/patches/propose",
        json={
            "session_id": "sess-123",
            "task_desc": "Need logging check",
            "budgets": {"tokens": 100, "latency_ms": 50},
            "slot_specs": [{"name": "task_header", "max_tokens": 50}],
        },
    )
    metrics = client.get("/metrics/dspy").json()
    assert metrics["entries"] >= 1

    FLAGS.set("dspy_logging", False)
    DATA_LOGGER.path.unlink(missing_ok=True)
    client.post(
        "/patches/propose",
        json={
            "session_id": "sess-123",
            "task_desc": "Need logging check",
            "budgets": {"tokens": 100, "latency_ms": 50},
            "slot_specs": [{"name": "task_header", "max_tokens": 50}],
        },
    )
    assert not DATA_LOGGER.path.exists()


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
    metrics_snapshot = client.get("/metrics/prometheus").text
    assert "gyre_consent_missing_total" in metrics_snapshot
    client.post("/governance/consent", json={"tenant": "demo", "project": "demo", "user": "sess-123", "consent": True})
    resp = client.post("/patches/inject", json={"patch": patch, "transport": "openai"})
    data = resp.json()
    assert data["ok"]
    assert data["transport"] == "openai"
    transport_metrics = client.get("/metrics/transports").json()
    assert transport_metrics["transports"]["openai"]["success"] >= 1
    scopes = transport_metrics["transports"]["openai"].get("scopes") or []
    assert any(scope["tenant"] == "demo" and scope.get("project") == "demo" for scope in scopes)
    client.post("/transports/chaos", json={"transport": "openai", "available": False})
    status = client.get("/transports/status").json()
    assert status["transports"]["openai"] is False


def test_feedback_endpoints(tmp_path):
    from server import run_dev_server as srv

    srv.FEEDBACK = FeedbackStore(tmp_path / "feedback.jsonl")
    PRIVATE.upsert({"id": "p-1", "session_id": "sess-123", "scope": {"tenant": "demo", "project": "demo", "user": "sess-123"}})
    resp = client.post(
        "/patches/feedback",
        json={"patch_id": "p-1", "session_id": "sess-123", "verdict": "accepted"},
    )
    assert resp.status_code == 200
    stats = client.get("/patches/feedback").json()
    assert stats["stats"]["accepted"] >= 1


def test_pilot_gating_blocks_disallowed_scope(tmp_path):
    from server import run_dev_server as srv

    cfg = tmp_path / "pilot.json"
    cfg.write_text('{"defaults":{"allow":false}}', encoding="utf-8")
    srv.PILOT = PilotRollout(cfg)
    seed_session()
    resp = client.post(
        "/patches/propose",
        json={
            "session_id": "sess-123",
            "task_desc": "Need gating test plan",
            "budgets": {"tokens": 100, "latency_ms": 50},
            "slot_specs": [{"name": "task_header", "max_tokens": 50}],
        },
    )
    assert resp.status_code == 403
    srv.PILOT = PilotRollout()


def test_transport_health_endpoint():
    resp = client.get("/health/transports").json()
    assert resp["status"] in {"ok", "degraded", "unknown"}
    assert resp["transports"]
    names = {info["name"] for info in resp["transports"]}
    assert "openai" in names


def test_learning_cycle_metric(monkeypatch, tmp_path):
    from server import run_dev_server as srv

    meta = tmp_path / "learning_cycle.json"
    meta.write_text('{"timestamp": 123456.0}', encoding="utf-8")
    monkeypatch.setattr(srv, "LEARNING_META_PATH", meta)
    resp = client.get("/metrics/prometheus")
    assert "gyre_learning_last_run_timestamp" in resp.text
