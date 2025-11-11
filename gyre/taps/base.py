from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence

import httpx


def _ensure_dt(value: Any) -> dt.datetime:
    """Normalize timestamps coming from providers or replay logs."""
    if isinstance(value, dt.datetime):
        return value
    if isinstance(value, (int, float)):
        return dt.datetime.fromtimestamp(value, tz=dt.timezone.utc)
    if isinstance(value, str):
        try:
            return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    # fallback to now
    return dt.datetime.now(dt.timezone.utc)


@dataclass
class TapEvent:
    """Canonical event envelope that Gyre expects on /observe/ingest."""

    timestamp: dt.datetime
    kind: str
    payload: Dict[str, Any]
    channel: Optional[str] = None
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_session_event(self) -> Dict[str, Any]:
        event = {
            "t": self.timestamp.isoformat(),
            "kind": self.kind,
            "payload": self.payload,
        }
        if self.channel:
            event["channel"] = self.channel
        if self.source:
            event["source"] = self.source
        if self.metadata:
            event["metadata"] = self.metadata
        return event

    @classmethod
    def from_raw(
        cls,
        *,
        timestamp: Any,
        kind: str,
        payload: Dict[str, Any],
        channel: Optional[str] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "TapEvent":
        return cls(
            timestamp=_ensure_dt(timestamp),
            kind=kind,
            payload=payload,
            channel=channel,
            source=source,
            metadata=metadata or {},
        )


class SessionTap:
    """Utility for pushing TapEvents into the Gyre observe endpoint."""

    def __init__(
        self,
        session_id: str,
        ingest_url: str,
        *,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self.session_id = session_id
        self.ingest_url = ingest_url
        self.client = http_client or httpx.Client(timeout=5.0)

    def emit(self, events: Sequence[TapEvent]) -> Dict[str, Any]:
        payload = {
            "session_id": self.session_id,
            "events": [event.to_session_event() for event in events],
        }
        response = self.client.post(self.ingest_url, json=payload)
        response.raise_for_status()
        return response.json()

    def emit_one(self, event: TapEvent) -> Dict[str, Any]:
        return self.emit([event])

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "SessionTap":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
