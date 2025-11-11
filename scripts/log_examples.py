#!/usr/bin/env python
"""Log Stage A/B examples from recorded `/patches/propose` responses."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract DSPy training rows from propose responses")
    parser.add_argument("--responses", required=True, help="JSONL of /patches/propose responses")
    parser.add_argument("--out", default="data/train", help="Output directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    responses = Path(args.responses)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rank_rows = []
    sum_rows = []
    stage_a_rows = []

    for line in responses.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        resp = json.loads(line)
        task = resp.get("task_desc") or ""
        candidates = resp.get("candidates", [])
        rank_rows.append({"task_desc": task, "items": candidates, "trace": resp.get("trace", [])})
        sum_rows.append({"slot":"retrieved_evidence","items": resp.get("patches", [])})
        stage_a_rows.append(resp.get("stage_a", {}))

    (out / "rank_train.jsonl").write_text("\n".join(json.dumps(r) for r in rank_rows), encoding="utf-8")
    (out / "sum_train.jsonl").write_text("\n".join(json.dumps(r) for r in sum_rows), encoding="utf-8")
    (out / "stage_a.jsonl").write_text("\n".join(json.dumps(r) for r in stage_a_rows), encoding="utf-8")


if __name__ == "__main__":
    main()
