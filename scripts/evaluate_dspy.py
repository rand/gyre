#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Any


def summarize(log_path: Path) -> Dict[str, Any]:
    if not log_path.exists():
        return {"entries": 0}
    totals = {"entries": 0, "stage_a_tokens": 0, "stage_b_tokens": 0, "selected": 0}
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        totals["entries"] += 1
        stage_a = entry.get("stage_a", {})
        ledger = entry.get("selection", {}).get("ledger", {})
        totals["stage_a_tokens"] += stage_a.get("ledger", {}).get("tokens_used", 0)
        totals["stage_b_tokens"] += ledger.get("tokens_used", 0)
        totals["selected"] += len(entry.get("selection", {}).get("selected", []))
    if totals["entries"]:
        totals["avg_stage_a_tokens"] = totals["stage_a_tokens"] / totals["entries"]
        totals["avg_stage_b_tokens"] = totals["stage_b_tokens"] / totals["entries"]
        totals["avg_selected"] = totals["selected"] / totals["entries"]
    return totals


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate DSPy logs")
    parser.add_argument("--log", default="data/logs/propose.jsonl")
    args = parser.parse_args()
    stats = summarize(Path(args.log))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
