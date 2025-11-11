from __future__ import annotations

import time
from typing import Any, Dict, List, Protocol

from . import openai_adapter, anthropic_adapter, gemini_adapter


class Transport(Protocol):
    name: str

    def send(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        ...


class StubTransport:
    def __init__(self, name: str):
        self.name = name
        self.available = True

    def ensure_available(self):
        if not self.available:
            raise RuntimeError(f"Transport {self.name} unavailable")

    def send(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class OpenAITransport(StubTransport):
    def __init__(self):
        super().__init__("openai")

    def send(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        self.ensure_available()
        text = flatten_blueprint(patch.get("body", {}))
        return openai_adapter.inject_system_prefix(patch["target_session_id"], text)


class AnthropicTransport(StubTransport):
    def __init__(self):
        super().__init__("anthropic")

    def send(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        self.ensure_available()
        text = flatten_blueprint(patch.get("body", {}))
        return anthropic_adapter.inject_message(patch["target_session_id"], text)


class GeminiTransport(StubTransport):
    def __init__(self):
        super().__init__("gemini")

    def send(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        self.ensure_available()
        payload = {
            "slots": patch.get("body", {}).get("slots", []),
            "note": patch.get("note"),
        }
        return gemini_adapter.inject_function_result(patch["target_session_id"], "context_patch", payload)


class TransportBroker:
    def __init__(self, transports: Dict[str, Transport], cooldown_seconds: float = 2.0):
        self.transports = transports
        self.failures: Dict[str, int] = {}
        self.cooldowns: Dict[str, float] = {}
        self.cooldown_seconds = cooldown_seconds

    @classmethod
    def default(cls) -> "TransportBroker":
        return cls(
            transports={
                "openai": OpenAITransport(),
                "anthropic": AnthropicTransport(),
                "gemini": GeminiTransport(),
            }
        )

    def inject(self, patch: Dict[str, Any], preferred: str = "best") -> Dict[str, Any]:
        order = self._route_order(preferred)
        errors = []
        for name in order:
            transport = self.transports.get(name)
            if not transport:
                continue
            if name in self.cooldowns and self.cooldowns[name] > time.time():
                continue
            try:
                ack = transport.send(patch)
                return {"transport": name, "ack": ack}
            except Exception as exc:
                self.failures[name] = self.failures.get(name, 0) + 1
                self.cooldowns[name] = time.time() + self.cooldown_seconds
                errors.append({"transport": name, "error": str(exc)})
        raise RuntimeError(f"All transports failed: {errors}")

    def _route_order(self, preferred: str) -> List[str]:
        if preferred == "best":
            return list(self.transports.keys())
        return [preferred] + [name for name in self.transports if name != preferred]

    def set_availability(self, name: str, available: bool) -> bool:
        transport = self.transports.get(name)
        if not transport or not isinstance(transport, StubTransport):
            return False
        transport.available = available
        if available and name in self.cooldowns:
            del self.cooldowns[name]
        return True

    def status(self) -> Dict[str, Any]:
        return {
            "failures": dict(self.failures),
            "cooldowns": {k: max(v - time.time(), 0.0) for k, v in self.cooldowns.items()},
            "transports": {name: getattr(t, "available", True) for name, t in self.transports.items()},
        }


def flatten_blueprint(blueprint: Dict[str, Any]) -> str:
    slots = blueprint.get("slots", [])
    parts = []
    for slot in slots:
        name = slot.get("name")
        content = slot.get("content")
        if content:
            parts.append(f"[{name}] {content}")
    return "\n\n".join(parts)
