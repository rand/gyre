from gyre.selector import select


class DummyRanker:
    def __init__(self, order):
        self.order = order

    def rank(self, task_desc, budgets, candidates):
        return self.order, {"mode": "test", "request": {"topk": len(self.order)}}


def test_select_respects_budgets():
    cands = [
        {"id": "1", "features": {"relevance": 0.9, "actionability": 0.8}, "costs": {"tokens_est": 100, "latency_est_ms": 10}, "risks": {"sensitivity": "low"}},
        {"id": "2", "features": {"relevance": 0.8, "actionability": 0.7}, "costs": {"tokens_est": 600, "latency_est_ms": 200}, "risks": {"sensitivity": "low"}},
    ]
    result = select(cands, {"tokens": 200, "latency_ms": 100})
    ids = [item["id"] for item in result["selected"]]
    assert "1" in ids and "2" not in ids
    assert result["ledger"]["tokens_used"] <= 200


def test_select_uses_ranker_bonus():
    cands = [
        {"id": "keep", "features": {"relevance": 0.5}, "costs": {"tokens_est": 100}, "risks": {"sensitivity": "low"}},
        {"id": "prefer", "features": {"relevance": 0.5}, "costs": {"tokens_est": 100}, "risks": {"sensitivity": "low"}},
    ]
    ranker = DummyRanker(["prefer", "keep"])
    result = select(
        cands,
        {"tokens": 500, "latency_ms": 500},
        task_desc="Need DSPy order",
        ranker=ranker,
        rank_weight=2.0,
    )
    assert result["trace"][0]["id"] == "prefer"
    assert result["ranker"]["mode"] == "test"
