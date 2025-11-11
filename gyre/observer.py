from __future__ import annotations

import datetime as dt
import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Sequence

MAX_TASK_DESC_LEN = 400
MAX_RECENT_EVENTS = 25
ENTITY_REGEX = re.compile(r"\b[A-Z][A-Za-z0-9_]+\b")


def infer_task_desc(events: Sequence[Dict[str, Any]]) -> str:
    """Prefer the latest user/agent utterance with textual payload."""
    for ev in reversed(events):
        kind = ev.get("kind")
        if kind not in ("user", "agent", "system"):
            continue
        text = _extract_text(ev.get("payload"))
        if text:
            return text[:MAX_TASK_DESC_LEN]
    # fallback to concatenated payload strings
    payloads = " ".join(_extract_text(ev.get("payload")) for ev in events if ev.get("payload"))
    return payloads[:MAX_TASK_DESC_LEN]


def observe(task_desc: str, events: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    normalized = [_normalize_event(ev) for ev in events]
    entities = _extract_entities(normalized)
    novelty = _novelty_report(normalized[-MAX_RECENT_EVENTS:])
    return {
        "task_desc": task_desc,
        "entities": entities,
        "recent_events": normalized[-MAX_RECENT_EVENTS:],
        "novelty": novelty,
    }


# ----------------------------
# Helpers


def _normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    timestamp = event.get("t") or event.get("timestamp") or dt.datetime.now(dt.timezone.utc).isoformat()
    text = _extract_text(event.get("payload"))
    kind = event.get("kind") or "agent"
    channel = event.get("channel")
    source = event.get("source")
    tokens_est = max(1, len(text.split())) if text else 0
    digest_src = "|".join(
        [
            kind or "",
            channel or "",
            source or "",
            text or "",
        ]
    )
    digest = hashlib.sha1(digest_src.encode("utf-8")).hexdigest()
    return {
        "t": timestamp,
        "kind": kind,
        "channel": channel,
        "source": source,
        "text": text,
        "tokens_est": tokens_est,
        "digest": digest,
        "raw": event,
    }


def _extract_text(payload: Any) -> str:
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        if "text" in payload and isinstance(payload["text"], str):
            return payload["text"]
        if "parts" in payload and isinstance(payload["parts"], list):
            return " ".join(_extract_text(part) for part in payload["parts"])
        return " ".join(str(value) for value in payload.values() if isinstance(value, (str, int, float)))
    if isinstance(payload, list):
        return " ".join(_extract_text(item) for item in payload)
    return str(payload)


def _extract_entities(events: Iterable[Dict[str, Any]]) -> List[str]:
    seen = []
    for ev in events:
        for match in ENTITY_REGEX.findall(ev.get("text") or ""):
            if match not in seen:
                seen.append(match)
            if len(seen) >= 25:
                return seen
    return seen


def _novelty_report(events: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if not events:
        return {"score": 0.0, "novel_events": []}
    seen_digests = set()
    novel = []
    for ev in events:
        digest = ev["digest"]
        if digest in seen_digests or not ev.get("text"):
            continue
        seen_digests.add(digest)
        novel.append(
            {
                "t": ev["t"],
                "kind": ev["kind"],
                "channel": ev["channel"],
                "text": ev["text"],
                "tokens_est": ev["tokens_est"],
            }
        )
    score = len(novel) / max(1, len(events))
    return {"score": round(score, 3), "novel_events": novel[:10]}
