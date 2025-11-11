from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol

from . import openai_adapter, anthropic_adapter, gemini_adapter


class Transport(Protocol):
    name: str

    def send(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        ...


@dataclass
class StubTransport:
    name: str

    def send(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


@dataclass
class OpenAITransport(StubTransport):
    name: str = "openai"

    def send(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        text = flatten_blueprint(patch.get("body", {}))
        return openai_adapter.inject_system_prefix(patch["target_session_id"], text)


@dataclass
class AnthropicTransport(StubTransport):
    name: str = "anthropic"

    def send(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        text = flatten_blueprint(patch.get("body", {}))
        return anthropic_adapter.inject_message(patch["target_session_id"], text)


@dataclass
class GeminiTransport(StubTransport):
    name: str = "gemini"

    def send(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "slots": patch.get("body", {}).get("slots", []),
            "note": patch.get("note"),
        }
        return gemini_adapter.inject_function_result(patch["target_session_id"], "context_patch", payload)


@dataclass
class TransportBroker:
    transports: Dict[str, Transport]
    failures: Dict[str, int] = field(default_factory=dict)

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
            try:
                ack = transport.send(patch)
                return {"transport": name, "ack": ack}
            except Exception as exc:
                self.failures[name] = self.failures.get(name, 0) + 1
                errors.append({"transport": name, "error": str(exc)})
        raise RuntimeError(f"All transports failed: {errors}")

    def _route_order(self, preferred: str) -> List[str]:
        if preferred == "best":
            return list(self.transports.keys())
        return [preferred] + [name for name in self.transports if name != preferred]


def flatten_blueprint(blueprint: Dict[str, Any]) -> str:
    slots = blueprint.get("slots", [])
    parts = []
    for slot in slots:
        name = slot.get("name")
        content = slot.get("content")
        if content:
            parts.append(f"[{name}] {content}")
    return "\n\n".join(parts)
