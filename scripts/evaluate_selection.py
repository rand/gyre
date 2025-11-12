#!/usr/bin/env python
"""
Offline evaluation harness for the Stage A/B planner + selector.

Usage:
    uv run python scripts/evaluate_selection.py --trace traces/example.jsonl \
        --budget-tokens 800 --budget-latency 800
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from gyre.planner import DeferredQueryPlanner
from gyre.selector import select
from gyre.retriever import retrieve


def load_candidates(path: Path) -> List[Dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data["candidates"]


def evaluate(trace_path: Path, budgets: Dict[str, int]) -> Dict[str, object]:
    planner = DeferredQueryPlanner.default()
    raw_candidates = load_candidates(trace_path)
    task_text = " ".join(c.get("content", {}).get("text", "") for c in raw_candidates)
    stage_a = planner.run(task_text, budgets, "eval")
    pool = raw_candidates + stage_a["executed"]
    retrieved = retrieve(" ".join(c.get("content", {}).get("text", "") for c in pool), pool)
    selection = select(retrieved, budgets, task_desc=task_text)
    return {
        "stage_a": stage_a["ledger"],
        "stage_b": selection["ledger"],
        "selected_ids": [c["id"] for c in selection["selected"]],
        "trace": selection["trace"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate selection pipeline")
    parser.add_argument("--trace", required=True, type=Path)
    parser.add_argument("--budget-tokens", type=int, default=800)
    parser.add_argument("--budget-latency", type=int, default=800)
    args = parser.parse_args()
    summary = evaluate(
        args.trace,
        {"tokens": args.budget_tokens, "latency_ms": args.budget_latency},
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
