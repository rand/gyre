from pathlib import Path
import json

from scripts.evaluate_selection import evaluate


def test_evaluate_selection(tmp_path):
    trace = tmp_path / "trace.json"
    trace.write_text(json.dumps([
        {"id": "cand-1", "kind": "memory", "content": {"text": "Plan coil springs"}, "features": {"relevance": 0.9}, "costs": {"tokens_est": 50, "latency_est_ms": 5}},
        {"id": "cand-2", "kind": "memory", "content": {"text": "Check incidents"}, "features": {"relevance": 0.5}, "costs": {"tokens_est": 60, "latency_est_ms": 5}},
    ]), encoding="utf-8")
    summary = evaluate(trace, {"tokens": 300, "latency_ms": 300})
    assert summary["stage_a"]["latency_ms_used"] <= 300
    assert summary["stage_b"]["tokens_used"] <= 300
    assert summary["selected_ids"]
