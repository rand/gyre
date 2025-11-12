from gyre.dspy_ranker import DSPYRanker


def test_dspy_ranker_returns_ids_and_journal():
    ranker = DSPYRanker(max_items=2)
    candidates = [
        {"id": "a", "features": {"relevance": 0.8}, "costs": {"tokens_est": 10}},
        {"id": "b", "features": {"relevance": 0.7}, "costs": {"tokens_est": 10}},
        {"id": "c", "features": {"relevance": 0.6}, "costs": {"tokens_est": 10}},
    ]
    ids, journal = ranker.rank("Need plan", {"tokens": 100}, candidates)
    assert ids[:2] == ["a", "b"]
    assert journal["request"]["topk"] == 2
    assert journal["response"]["ids"]
