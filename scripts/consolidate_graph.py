#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

from gyre.stores.graph_store import TemporalGraph


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run temporal graph consolidation")
    parser.add_argument("--path", default="data/graph.json", help="Graph JSON path")
    parser.add_argument("--ttl-hours", type=int, default=24)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    graph = TemporalGraph(Path(args.path))
    removed = graph.consolidate(ttl_hours=args.ttl_hours)
    print(f"Removed {removed} expired nodes from graph {args.path}")


+if __name__ == "__main__":
+    main()
