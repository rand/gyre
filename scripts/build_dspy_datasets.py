#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from gyre import datasets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build DSPy training datasets from propose logs")
    parser.add_argument("--log", default="data/logs/propose.jsonl", help="Path to DatasetLogger JSONL")
    parser.add_argument("--out", default="data/train", help="Output directory for dataset files")
    parser.add_argument("--train-ratio", type=float, default=0.8, help="Proportion of rows assigned to train splits")
    parser.add_argument("--max-items", type=int, default=50, help="Maximum pool items per ranking record")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    log_path = Path(args.log)
    entries = datasets.load_entries(log_path)
    feedbacks = datasets.load_feedback_map(log_path.parent.parent / "feedback.jsonl")
    summary = datasets.build_and_write(
        entries,
        Path(args.out),
        train_ratio=args.train_ratio,
        max_items=args.max_items,
        feedbacks=feedbacks,
    )
    print(json.dumps({"log_entries": len(entries), "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
