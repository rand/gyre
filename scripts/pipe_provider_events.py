#!/usr/bin/env python
"""
Feed provider-specific event logs into Gyre via the tap adapters.

Usage:
    uv run python scripts/pipe_provider_events.py \
        --provider openai --session demo --trace data/logs/openai.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List, Dict

from gyre.taps import OpenAIRealtimeTap, AnthropicTap


PROVIDERS = {
    "openai": OpenAIRealtimeTap,
    "anthropic": AnthropicTap,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipe provider events into Gyre")
    parser.add_argument("--provider", choices=PROVIDERS.keys(), required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--trace", type=Path, required=True, help="JSON or JSONL log")
    parser.add_argument(
        "--ingest-url",
        default="http://localhost:8000/observe/ingest",
        help="Gyre ingest endpoint",
    )
    parser.add_argument("--batch-size", type=int, default=30)
    return parser.parse_args()


def load_messages(path: Path) -> List[Dict[str, object]]:
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        messages = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                messages.append(json.loads(line))
        return messages
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else [data]


def main() -> None:
    args = parse_args()
    tap_cls = PROVIDERS[args.provider]
    messages = load_messages(args.trace)
    tap = tap_cls(args.session, args.ingest_url)
    try:
        for chunk_start in range(0, len(messages), args.batch_size):
            chunk = messages[chunk_start : chunk_start + args.batch_size]
            tap.handle_messages(chunk)
    finally:
        tap.close()


if __name__ == "__main__":
    main()
