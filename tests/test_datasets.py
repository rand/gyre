from pathlib import Path

from gyre import datasets


def sample_entry(session_id: str) -> dict:
    return {
        "session_id": session_id,
        "task_desc": f"Task {session_id}",
        "budgets": {"tokens": 500},
        "pool": [
            {"id": f"{session_id}-a", "features": {"relevance": 0.8}},
            {"id": f"{session_id}-b", "features": {"relevance": 0.6}},
        ],
        "selection": {
            "selected": [{"id": f"{session_id}-a"}],
            "trace": [{"id": f"{session_id}-a", "gain": 1.0}],
            "ledger": {"tokens_used": 100},
        },
        "stage_a": {
            "plans": [
                {"id": f"deferred:{session_id}:parts", "provider": "parts_api"},
                {"id": f"deferred:{session_id}:status", "provider": "status"},
            ],
            "executed": [f"tool:{session_id}:parts"],  # tool ids (legacy)
            "executed_plan_ids": [f"deferred:{session_id}:parts"],
            "ledger": {"tokens_used": 200},
        },
        "patch": {
            "body": {"slots": [{"name": "task_header", "content": "Header"}]},
            "body_unredacted": {
                "slots": [{"name": "task_header", "content": "Header"}],
            },
        },
        "slot_specs": [{"name": "task_header", "max_tokens": 100}],
    }


def test_build_and_write_creates_dataset_files(tmp_path):
    entries = [sample_entry("s1"), sample_entry("s2")]
    out_dir = tmp_path / "train"
    summary = datasets.build_and_write(entries, out_dir, train_ratio=0.5, max_items=10)
    assert summary["entries"] == 2
    for name in ("rank_train", "rank_eval", "sum_train", "sum_eval", "ev_train", "ev_eval"):
        path = out_dir / f"{name}.jsonl"
        assert path.exists()
        content = path.read_text(encoding="utf-8").strip()
        if content:
            assert content.count("\n") >= 0
