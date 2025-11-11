from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Iterable, List, Optional

from .base import SessionTap, TapEvent


TYPE_KIND_MAP = {
    "input_text.delta": "user",
    "message_start": "agent",
    "message_delta": "agent",
    "message_stop": "agent",
    "content_block_start": "agent",
    "content_block_delta": "agent",
    "content_block_stop": "agent",
    "tool_start": "tool",
    "tool_delta": "tool",
    "tool_output": "tool",
    "tool_stop": "tool",
    "error": "system",
}


def as_claude_event(message: Dict[str, Any]) -> Optional[TapEvent]:
    timestamp = (
        message.get("timestamp")
        or message.get("created_at")
        or dt.datetime.now(dt.timezone.utc).isoformat()
    )
    event_type = message.get("type")
    kind = TYPE_KIND_MAP.get(event_type, message.get("kind", "agent"))

    payload = {}
    if "content" in message:
        payload["content"] = message["content"]
    if "delta" in message:
        payload["delta"] = message["delta"]
    if "input" in message and isinstance(message["input"], str):
        payload["text"] = message["input"]
    if "label" in message:
        payload["label"] = message["label"]

    metadata = {}
    for key in ("id", "message_id", "tool_id", "conversation_id"):
        if key in message:
            metadata[key] = message[key]
    if event_type:
        metadata["type"] = event_type

    channel = message.get("conversation_id")
    source = "anthropic"
    return TapEvent.from_raw(
        timestamp=timestamp,
        kind=kind,
        payload=payload,
        channel=channel,
        source=source,
        metadata=metadata,
    )


class AnthropicTap(SessionTap):
    """Adapter for Anthropic Claude (Computer Use / Messages) streams."""

    def handle_messages(self, messages: Iterable[Dict[str, Any]]) -> None:
        events: List[TapEvent] = []
        for msg in messages:
            event = as_claude_event(msg)
            if event:
                events.append(event)
        if events:
            self.emit(events)
