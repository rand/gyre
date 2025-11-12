#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from gyre.metrics import summarize_propose_logs


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate DSPy logs")
    parser.add_argument("--log", default="data/logs/propose.jsonl")
    args = parser.parse_args()
    stats = summarize_propose_logs(Path(args.log))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
