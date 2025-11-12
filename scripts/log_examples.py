#!/usr/bin/env python
"""Extract DSPy training datasets from `data/logs/propose.jsonl`."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract DSPy training rows from propose logs")
    parser.add_argument("--log", default="data/logs/propose.jsonl", help="Dataset log emitted by DatasetLogger")
    parser.add_argument("--out", default="data/train", help="Output directory")
    parser.add_argument("--max-items", type=int, default=50, help="Limit the number of candidates per record")
    return parser.parse_args()


def load_entries(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entries.append(json.loads(line))
    return entries


def ranked_ids(entry: Dict[str, Any]) -> List[str]:
    selection = entry.get("selection", {})
    trace = selection.get("trace", [])
    ids = [step["id"] for step in trace if step.get("id")]
    if ids:
        return ids
    chosen = selection.get("selected", [])
    return [item.get("id") for item in chosen if item.get("id")]


def build_rank_row(entry: Dict[str, Any], max_items: int) -> Dict[str, Any]:
    pool = entry.get("pool") or entry.get("candidates") or []
    trimmed = pool[:max_items]
    ids = ranked_ids(entry)
    return {
        "task_desc": entry.get("task_desc", ""),
        "budget_tokens": entry.get("budgets", {}).get("tokens", 0),
        "items_json": json.dumps(trimmed),
        "topk": len(ids),
        "ranked_ids_json": json.dumps(ids),
    }


def build_sum_rows(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    patch = entry.get("patch", {})
    blueprint = patch.get("body_unredacted") or patch.get("body") or {}
    slots = blueprint.get("slots") if isinstance(blueprint, dict) else []
    rows = []
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
                    "tokens": slot.get("tokens"),
                }
            )
    return rows


def main() -> None:
    args = parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    entries = load_entries(Path(args.log))

    rank_rows = [build_rank_row(entry, args.max_items) for entry in entries if entry.get("selection")]
    sum_rows: List[Dict[str, Any]] = []
    stage_a_rows = [entry.get("stage_a", {}) for entry in entries if entry.get("stage_a")]
    for entry in entries:
        sum_rows.extend(build_sum_rows(entry))

    (out / "rank_train.jsonl").write_text("\n".join(json.dumps(r) for r in rank_rows), encoding="utf-8")
    (out / "sum_train.jsonl").write_text("\n".join(json.dumps(r) for r in sum_rows), encoding="utf-8")
    (out / "stage_a.jsonl").write_text("\n".join(json.dumps(r) for r in stage_a_rows), encoding="utf-8")


if __name__ == "__main__":
    main()
