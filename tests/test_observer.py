from gyre import observer


def test_infer_task_desc_prefers_latest_user():
    events = [
        {"kind": "agent", "payload": {"text": "response"}},
        {"kind": "user", "payload": {"text": "Need spec"}},
    ]
    assert observer.infer_task_desc(events) == "Need spec"


def test_observe_outputs_novelty_and_entities():
    events = [
        {"t": "2025-02-15T00:00:00Z", "kind": "user", "payload": {"text": "Work on DenverSuspension plan"}},
        {"t": "2025-02-15T00:00:10Z", "kind": "agent", "payload": {"text": "DenverSuspension requires EPACompliance"}}]
    state = observer.observe("Work on DenverSuspension plan", events)
    assert "DenverSuspension" in state["entities"]
    assert state["novelty"]["score"] > 0
    assert state["recent_events"][-1]["text"].startswith("Denver")
