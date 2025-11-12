import json
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
            {"id": f"{session_id}-c", "features": {"relevance": 0.4}},
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


def test_build_and_write_accepts_feedback(tmp_path):
    entry = sample_entry("s3")
    entry["patch"]["id"] = "patch-s3"
    out_dir = tmp_path / "train"
    summary = datasets.build_and_write(
        [entry],
        out_dir,
        train_ratio=1.0,
        max_items=10,
        feedbacks={"patch-s3": {"verdict": "accepted"}},
    )
    assert summary["rank"]["accepted"] == 1


def test_negative_sampling_and_weights(tmp_path):
    entry = sample_entry("s4")
    entry["patch"]["id"] = "patch-s4"
    out_dir = tmp_path / "train"
    datasets.build_and_write(
        [entry],
        out_dir,
        train_ratio=1.0,
        max_items=10,
        feedbacks={"patch-s4": {"verdict": "rejected"}},
        feedback_weights={"rejected": 0.1},
        default_weight=1.0,
        negative_samples=2,
    )
    rank_path = out_dir / "rank_train.jsonl"
    data = rank_path.read_text(encoding="utf-8").strip().splitlines()
    record = json.loads(data[0])
    assert record["weight"] == 0.1
    assert set(record.get("negative_ids", [])) <= {"s4-b", "s4-c"}
