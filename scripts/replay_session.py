#!/usr/bin/env python
"""
Replay a session trace (JSON/JSONL) into the local Gyre dev server.

Usage:
    uv run python scripts/replay_session.py --session my-session \
        --trace data/traces/example.jsonl
"""

from __future__ import annotations

import argparse
from pathlib import Path

from gyre.taps import ReplayTap


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay a trace into Gyre")
    parser.add_argument("--session", required=True, help="Session identifier")
    parser.add_argument(
        "--ingest-url",
        default="http://localhost:8000/observe/ingest",
        help="Gyre /observe/ingest endpoint",
    )
    parser.add_argument(
        "--trace",
        required=True,
        type=Path,
        help="Path to JSON or JSONL trace file",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Number of events per POST",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tap = ReplayTap(session_id=args.session, ingest_url=args.ingest_url)
    tap.stream_file(args.trace, batch_size=args.batch_size)
    tap.close()


if __name__ == "__main__":
    main()
