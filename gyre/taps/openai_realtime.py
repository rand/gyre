from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Iterable, List, Optional

from .base import SessionTap, TapEvent, _ensure_dt


ROLE_KIND_MAP = {
    "user": "user",
    "assistant": "agent",
    "tool": "tool",
    "system": "system",
}

TYPE_KIND_MAP = {
    "response.error": "system",
    "conversation.item.completed": "agent",
    "conversation.item.created": "agent",
    "conversation.input_audio_buffer.speech_started": "audio",
    "conversation.input_audio_buffer.speech_stopped": "audio",
    "conversation.input_text.delta": "user",
    "response.completed": "agent",
}


def as_realtime_event(message: Dict[str, Any]) -> Optional[TapEvent]:
    """
    Convert an OpenAI Realtime message into a TapEvent.

    We only rely on commonly available fields so the adapter works for both
    ChatCompletions and Realtime streams.
    """
    timestamp = message.get("created", dt.datetime.now(dt.timezone.utc).isoformat())
    role = message.get("role")
    event_type = message.get("type")
    content = message.get("content") or message.get("delta") or {}

    kind = (
        ROLE_KIND_MAP.get(role)
        or TYPE_KIND_MAP.get(event_type)
        or message.get("kind")
        or "agent"
    )

    payload: Dict[str, Any] = {}
    if isinstance(content, list):
        payload["parts"] = content
    elif isinstance(content, dict):
        payload.update(content)
    elif content:
        payload["text"] = content

    metadata = {
        k: message[k]
        for k in ("id", "event_id", "response_id")
        if k in message
    }
    if event_type:
        metadata["type"] = event_type
    if role:
        metadata["role"] = role

    channel = message.get("conversation_id") or message.get("session_id")
    source = "openai.realtime"

    return TapEvent.from_raw(
        timestamp=timestamp,
        kind=kind,
        payload=payload,
        channel=channel,
        source=source,
        metadata=metadata,
    )


class OpenAIRealtimeTap(SessionTap):
    """
    Convenience wrapper for sending OpenAI Realtime messages into Gyre.

    Usage:
        tap = OpenAIRealtimeTap("sess-123", "http://localhost:8000/observe/ingest")
        tap.handle_messages(stream_events)
    """

    def handle_messages(self, messages: Iterable[Dict[str, Any]]) -> None:
        events: List[TapEvent] = []
        for msg in messages:
            event = as_realtime_event(msg)
            if event:
                events.append(event)
        if events:
            self.emit(events)
