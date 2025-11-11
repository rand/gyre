#!/usr/bin/env python
"""
Minimal reviewer CLI for listing candidates and exporting manual patches.

Example:
    uv run python scripts/reviewer_cli.py list --session demo
    uv run python scripts/reviewer_cli.py export --session demo --candidates evt:demo:1
"""

from __future__ import annotations

import argparse
import json
from typing import List

import httpx

DEFAULT_SLOTS = [
    {"name": "task_header", "max_tokens": 200},
    {"name": "retrieved_evidence", "max_tokens": 600},
    {"name": "citations", "max_tokens": 120},
]


def get_client(base_url: str) -> httpx.Client:
    return httpx.Client(base_url=base_url, timeout=10.0)


def cmd_list(args: argparse.Namespace) -> None:
    with get_client(args.base_url) as client:
        resp = client.get("/review/candidates", params={"session_id": args.session, "limit": args.limit})
        resp.raise_for_status()
        data = resp.json()
    print(f"Session {data['session_id']} — {len(data['candidates'])} candidates")
    for item in data["candidates"]:
        text = item.get("content", {}).get("text", "")
        preview = (text[:80] + "...") if len(text) > 80 else text
        print(f"- {item['id']} | rel={item['features'].get('relevance',0):.2f} | novelty={item.get('content',{}).get('novel_events', []) != []}")
        print(f"    {preview}")


def cmd_export(args: argparse.Namespace) -> None:
    candidate_ids = [c.strip() for c in args.candidates.split(",") if c.strip()]
    slots = DEFAULT_SLOTS
    if args.slots:
        slots = []
        for spec in args.slots.split(","):
            name, cap = spec.split(":")
            slots.append({"name": name, "max_tokens": int(cap)})
    payload = {
        "session_id": args.session,
        "candidate_ids": candidate_ids,
        "slot_specs": slots,
        "note": args.note,
    }
    with get_client(args.base_url) as client:
        resp = client.post("/review/export_patch", json=payload)
        resp.raise_for_status()
        data = resp.json()
    print("Exported patch:")
    print(json.dumps(data["patch"], indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Reviewer CLI")
    parser.add_argument("--base-url", default="http://localhost:8000")
    sub = parser.add_subparsers(dest="command")

    list_cmd = sub.add_parser("list", help="List recent candidates")
    list_cmd.add_argument("--session", required=True)
    list_cmd.add_argument("--limit", type=int, default=20)
    list_cmd.set_defaults(func=cmd_list)

    export_cmd = sub.add_parser("export", help="Export manual patch")
    export_cmd.add_argument("--session", required=True)
    export_cmd.add_argument("--candidates", required=True, help="Comma-separated candidate IDs")
    export_cmd.add_argument("--note", default="")
    export_cmd.add_argument("--slots", help="Override slots as name:cap,name:cap")
    export_cmd.set_defaults(func=cmd_export)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
