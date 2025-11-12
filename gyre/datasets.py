from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def load_entries(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    entries: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        entries.append(json.loads(line))
    return entries


def load_feedback_map(path: Path | None) -> Dict[str, Dict[str, Any]]:
    if not path or not path.exists():
        return {}
    mapping: Dict[str, Dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        mapping[row.get("patch_id", "")] = row
    return mapping


def partition(key: str, train_ratio: float) -> str:
    if not key:
        key = "default"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    return "train" if bucket < train_ratio else "eval"


def build_rank_record(entry: Dict[str, Any], max_items: int, feedbacks: Dict[str, Dict[str, Any]]) -> Dict[str, Any] | None:
    pool = entry.get("pool") or []
    if not pool:
        return None
    selected_ids = [
        item.get("id")
        for item in entry.get("selection", {}).get("selected", [])
        if item.get("id")
    ]
    patch_id = entry.get("patch", {}).get("id")
    feedback = feedbacks.get(patch_id or "") if patch_id else None
    return {
        "task_desc": entry.get("task_desc", ""),
        "session_id": entry.get("session_id"),
        "budgets": entry.get("budgets", {}),
        "items": pool[:max_items],
        "positive_ids": selected_ids,
        "verdict": (feedback or {}).get("verdict"),
        "weight": 1.0 if not feedback else (1.0 if feedback.get("verdict") == "accepted" else 0.25),
        "trace": entry.get("selection", {}).get("trace", []),
    }


def build_summary_rows(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    patch = entry.get("patch") or {}
    body = patch.get("body_unredacted") or patch.get("body") or {}
    slots = body.get("slots") if isinstance(body, dict) else []
    rows: List[Dict[str, Any]] = []
    if isinstance(slots, list):
        for slot in slots:
            if not isinstance(slot, dict):
                continue
            rows.append(
                {
                    "task_desc": entry.get("task_desc", ""),
                    "slot_name": slot.get("name"),
                    "content": slot.get("content"),
                    "citations": slot.get("citations", []),
                    "tokens": slot.get("tokens", 0),
                }
            )
    return rows


def build_stage_a_rows(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    stage_a = entry.get("stage_a") or {}
    plans = stage_a.get("plans") or []
    executed = set(stage_a.get("executed_plan_ids") or stage_a.get("executed") or [])
    rows: List[Dict[str, Any]] = []
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        rows.append(
            {
                "task_desc": entry.get("task_desc", ""),
                "plan": plan,
                "executed": plan.get("id") in executed,
            }
        )
    return rows


def build_redaction_rows(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    patch = entry.get("patch") or {}
    raw = patch.get("body_unredacted")
    redacted = patch.get("body")
    if not isinstance(raw, dict) or not isinstance(redacted, dict):
        return []
    return [
        {
            "task_desc": entry.get("task_desc", ""),
            "blueprint": raw,
            "redacted": redacted,
        }
    ]


def build_blueprint_rows(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    patch = entry.get("patch") or {}
    body = patch.get("body_unredacted")
    if not isinstance(body, dict):
        return []
    return [
        {
            "task_desc": entry.get("task_desc", ""),
            "slot_specs": entry.get("slot_specs", []),
            "selected": entry.get("selection", {}).get("selected", []),
            "blueprint": body,
        }
    ]


def build_datasets(
    entries: Iterable[Dict[str, Any]],
    *,
    train_ratio: float,
    max_items: int,
    feedbacks: Dict[str, Dict[str, Any]] | None = None,
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    feedbacks = feedbacks or {}
    datasets: Dict[str, List[Dict[str, Any]]] = {
        "rank_train": [],
        "rank_eval": [],
        "sum_train": [],
        "sum_eval": [],
        "ev_train": [],
        "ev_eval": [],
        "red_train": [],
        "red_eval": [],
        "blue_train": [],
        "blue_eval": [],
    }
    stats = {
        "entries": 0,
        "rank": {"train": 0, "eval": 0, "avg_positive": 0.0, "accepted": 0, "rejected": 0},
        "sum": {"rows": 0},
        "ev": {"rows": 0, "exec_rate": 0.0},
        "red": {"rows": 0},
        "blue": {"rows": 0},
    }
    total_positive = 0
    total_ev = 0
    executed_labels = 0

    for entry in entries:
        stats["entries"] += 1
        key = entry.get("session_id") or entry.get("task_desc", "")
        split = partition(key, train_ratio)

        rank_record = build_rank_record(entry, max_items, feedbacks)
        if rank_record and rank_record["items"]:
            datasets[f"rank_{split}"].append(rank_record)
            stats["rank"][split] += 1
            total_positive += len(rank_record.get("positive_ids", []))
            verdict = (rank_record.get("verdict") or "").lower()
            if verdict in ("accepted", "rejected"):
                stats["rank"][verdict] += 1

        sum_rows = build_summary_rows(entry)
        datasets[f"sum_{split}"].extend(sum_rows)
        stats["sum"]["rows"] += len(sum_rows)

        ev_rows = build_stage_a_rows(entry)
        datasets[f"ev_{split}"].extend(ev_rows)
        stats["ev"]["rows"] += len(ev_rows)
        executed_labels += sum(1 for row in ev_rows if row.get("executed"))
        total_ev += len(ev_rows)

        red_rows = build_redaction_rows(entry)
        datasets[f"red_{split}"].extend(red_rows)
        stats["red"]["rows"] += len(red_rows)

        blue_rows = build_blueprint_rows(entry)
        datasets[f"blue_{split}"].extend(blue_rows)
        stats["blue"]["rows"] += len(blue_rows)

    stats["rank"]["avg_positive"] = (
        total_positive / max(1, stats["rank"]["train"] + stats["rank"]["eval"])
    )
    stats["ev"]["exec_rate"] = executed_labels / max(1, total_ev)
    return datasets, stats


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def build_and_write(
    entries: Iterable[Dict[str, Any]],
    out_dir: Path,
    *,
    train_ratio: float,
    max_items: int,
) -> Dict[str, Any]:
    datasets, stats = build_datasets(entries, train_ratio=train_ratio, max_items=max_items)
    for name, rows in datasets.items():
        write_jsonl(out_dir / f"{name}.jsonl", rows)
    return stats
