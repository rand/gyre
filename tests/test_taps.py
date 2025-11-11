import datetime as dt
import json
from pathlib import Path

import httpx

from gyre.taps import TapEvent, OpenAIRealtimeTap, as_realtime_event, AnthropicTap, as_claude_event
from gyre.taps import replay as replay_mod


def test_tap_event_round_trip():
    now = dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc)
    event = TapEvent.from_raw(
        timestamp=now.isoformat(),
        kind="user",
        payload={"text": "hello"},
        channel="chat",
        metadata={"foo": "bar"},
    )
    assert event.to_session_event() == {
        "t": now.isoformat(),
        "kind": "user",
        "payload": {"text": "hello"},
        "channel": "chat",
        "metadata": {"foo": "bar"},
    }


def test_openai_adapter_maps_roles():
    msg = {
        "created": "2025-02-15T00:00:00Z",
        "role": "user",
        "content": [{"type": "input_text", "text": "hi"}],
        "id": "conv-1",
        "type": "conversation.item.created",
    }
    event = as_realtime_event(msg)
    assert event.kind == "user"
    assert event.payload["parts"][0]["text"] == "hi"
    assert event.metadata["type"] == "conversation.item.created"


def test_replay_tap_streams_jsonl(tmp_path):
    trace = tmp_path / "trace.jsonl"
    trace.write_text(
        json.dumps({"t": "2025-02-15T00:00:00Z", "kind": "user", "payload": {"text": "hi"}})
        + "\n",
        encoding="utf-8",
    )
    captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content.decode()))
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    tap = replay_mod.ReplayTap("sess-1", "https://example.com/observe/ingest", http_client=client)
    tap.stream_file(trace, batch_size=1)

    assert captured[0]["session_id"] == "sess-1"
    assert captured[0]["events"][0]["payload"]["text"] == "hi"


def test_anthropic_adapter_basic():
    msg = {"type": "message_start", "content": [{"type": "text", "text": "hello"}], "id": "msg-1"}
    event = as_claude_event(msg)
    assert event.kind == "agent"
    assert event.metadata["id"] == "msg-1"
