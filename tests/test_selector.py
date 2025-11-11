from gyre.selector import select


def test_select_respects_budgets():
    cands = [
        {"id": "1", "features": {"relevance": 0.9, "actionability": 0.8}, "costs": {"tokens_est": 100, "latency_est_ms": 10}, "risks": {"sensitivity": "low"}},
        {"id": "2", "features": {"relevance": 0.8, "actionability": 0.7}, "costs": {"tokens_est": 600, "latency_est_ms": 200}, "risks": {"sensitivity": "low"}},
    ]
    result = select(cands, {"tokens": 200, "latency_ms": 100})
    ids = [item["id"] for item in result["selected"]]
    assert "1" in ids and "2" not in ids
    assert result["ledger"]["tokens_used"] <= 200
