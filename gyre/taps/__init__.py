"""
Session tap helpers for mirroring provider-specific streams into Gyre's
canonical /observe/ingest API.

The `SessionTap` base handles batching events and posting them to the dev
server; provider-specific adapters live in sibling modules.
"""

from .base import SessionTap, TapEvent
from .openai_realtime import OpenAIRealtimeTap, as_realtime_event
from .anthropic import AnthropicTap, as_claude_event
from .replay import ReplayTap

__all__ = [
    "SessionTap",
    "TapEvent",
    "OpenAIRealtimeTap",
    "as_realtime_event",
    "AnthropicTap",
    "as_claude_event",
    "ReplayTap",
]
