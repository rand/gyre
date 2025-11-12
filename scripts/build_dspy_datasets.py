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
    parser.add_argument("--feedback", default="data/feedback.jsonl", help="Optional feedback JSONL path (set to 'none' to disable)")
    parser.add_argument("--accepted-weight", type=float, default=1.0, help="Weight applied to accepted verdicts")
    parser.add_argument("--rejected-weight", type=float, default=0.25, help="Weight applied to rejected verdicts")
    parser.add_argument("--default-weight", type=float, default=1.0, help="Weight when no verdict is present")
    parser.add_argument("--negative-samples", type=int, default=0, help="Number of negative IDs to sample for rejected verdicts")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    log_path = Path(args.log)
    entries = datasets.load_entries(log_path)
    feedback_path = args.feedback
    feedbacks = {}
    if feedback_path.lower() != "none":
        feedbacks = datasets.load_feedback_map(Path(feedback_path))
    summary = datasets.build_and_write(
        entries,
        Path(args.out),
        train_ratio=args.train_ratio,
        max_items=args.max_items,
        feedbacks=feedbacks,
        feedback_weights={"accepted": args.accepted_weight, "rejected": args.rejected_weight},
        default_weight=args.default_weight,
        negative_samples=args.negative_samples,
    )
    print(json.dumps({"log_entries": len(entries), "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
