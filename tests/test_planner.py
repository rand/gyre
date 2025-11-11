from gyre.planner import DeferredQueryPlanner


def test_planner_generates_and_executes():
    planner = DeferredQueryPlanner.default()
    plan = planner.run("Need parts plan", {"latency_ms": 300, "tokens": 500}, "sess-1")
    assert plan["deferred"]
    assert plan["executed"]
    assert plan["ledger"]["latency_ms_used"] <= 300
    assert plan["executed"][0]["session_id"] == "sess-1"
