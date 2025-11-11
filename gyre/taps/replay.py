from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from .base import SessionTap, TapEvent


class ReplayTap(SessionTap):
    """
    Streams events from a JSON/JSONL trace and forwards them to Gyre.

    A trace row can either be a dict already matching the ingest schema or any
    object accepted by TapEvent.from_raw.
    """

    def stream_file(self, path: Path, *, batch_size: int = 20) -> None:
        events = list(_load_events(path))
        for start in range(0, len(events), batch_size):
            self.emit(events[start : start + batch_size])


def _load_events(path: Path) -> Iterator[TapEvent]:
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                obj = json.loads(line)
                yield _to_event(obj)
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            for obj in data:
                yield _to_event(obj)
        else:
            yield _to_event(data)


def _to_event(obj) -> TapEvent:
    if isinstance(obj, dict) and {"t", "kind", "payload"}.issubset(obj.keys()):
        return TapEvent.from_raw(
            timestamp=obj["t"],
            kind=obj["kind"],
            payload=obj["payload"],
            channel=obj.get("channel"),
            source=obj.get("source"),
            metadata=obj.get("metadata"),
        )
    if not isinstance(obj, dict):
        raise ValueError("Trace rows must be objects or ingest-ready dicts.")
    return TapEvent.from_raw(
        timestamp=obj.get("timestamp") or obj.get("t"),
        kind=obj.get("kind", "agent"),
        payload=obj.get("payload") or {"text": obj.get("text", "")},
        channel=obj.get("channel"),
        source=obj.get("source"),
        metadata=obj.get("metadata"),
    )
