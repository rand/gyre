#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

from gyre.stores.graph_store import TemporalGraph
from gyre.skills import SkillRegistry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote skill candidates from temporal graph")
    parser.add_argument("--path", default="data/graph.json", help="Graph JSON path")
    parser.add_argument("--min-references", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    graph = TemporalGraph(Path(args.path))
    promoted = graph.promote_skills(min_references=args.min_references)
    registry = SkillRegistry()
    synced = registry.sync(graph.get_skills())
    print(f"Promoted {promoted} skills and synced {synced} entries from {args.path}")


if __name__ == "__main__":
    main()
