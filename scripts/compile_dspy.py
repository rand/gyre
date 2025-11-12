#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from gyre import programs


def load_dataset(path: Path) -> list:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile DSPy programs from logged datasets")
    parser.add_argument("--data-dir", default="data/train")
    args = parser.parse_args()

    base = Path(args.data_dir)
    datasets = {
        "rank_train": load_dataset(base / "rank_train.jsonl"),
        "sum_train": load_dataset(base / "sum_train.jsonl"),
        "ev_train": load_dataset(base / "ev_train.jsonl"),
        "red_train": load_dataset(base / "red_train.jsonl"),
        "blue_train": load_dataset(base / "blue_train.jsonl"),
    }
    programs.compile_programs(datasets)
    print("Compiled DSPy programs using datasets in", base)


if __name__ == "__main__":
    main()
