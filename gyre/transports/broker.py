from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple

from gyre.metrics_exporter import (
    record_transport_failure,
    record_transport_success,
)

from . import openai_adapter, anthropic_adapter, gemini_adapter
from .config import TransportConfig


class Transport(Protocol):
    name: str

    def send(self, patch: Dict[str, Any], *, credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ...


class BaseTransport:
    def __init__(self, name: str):
        self.name = name
        self.available = True

    def ensure_available(self) -> None:
        if not self.available:
            raise RuntimeError(f"Transport {self.name} unavailable")


class OpenAITransport(BaseTransport):
    def __init__(self, client: openai_adapter.OpenAIClient | None = None):
        super().__init__("openai")
        self.client = client or openai_adapter.OpenAIClient()

    def send(self, patch: Dict[str, Any], *, credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.ensure_available()
        text = flatten_blueprint(patch.get("body", {}))
        return self.client.send_system_prefix(patch["target_session_id"], text, credentials=credentials)


class AnthropicTransport(BaseTransport):
    def __init__(self, client: anthropic_adapter.AnthropicClient | None = None):
        super().__init__("anthropic")
        self.client = client or anthropic_adapter.AnthropicClient()

    def send(self, patch: Dict[str, Any], *, credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.ensure_available()
        text = flatten_blueprint(patch.get("body", {}))
        return self.client.inject_message(patch["target_session_id"], text, credentials=credentials)


class GeminiTransport(BaseTransport):
    def __init__(self, client: gemini_adapter.GeminiClient | None = None):
        super().__init__("gemini")
        self.client = client or gemini_adapter.GeminiClient()

    def send(self, patch: Dict[str, Any], *, credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.ensure_available()
        payload = {
            "slots": patch.get("body", {}).get("slots", []),
            "note": patch.get("note"),
        }
        return self.client.inject_function_result(
            patch["target_session_id"],
            "context_patch",
            payload,
            credentials=credentials,
        )


@dataclass
@dataclass
class ScopeStats:
    success: int = 0
    failure: int = 0
    last_error: str | None = None
    last_latency_ms: float = 0.0


@dataclass
class TransportStats:
    success: int = 0
    failure: int = 0
    latency_ms_total: float = 0.0
    latency_ms_last: float = 0.0
    last_error: str | None = None
    scopes: Dict[Tuple[str, str], ScopeStats] = field(default_factory=dict)

    @property
    def avg_latency_ms(self) -> float:
        return self.latency_ms_total / max(1, self.success)


class TransportMetrics:
    def __init__(self):
        self._lock = threading.Lock()
        self._stats: Dict[str, TransportStats] = {}

    def _scope_key(self, tenant: str, project: Optional[str]) -> Tuple[str, str]:
        return tenant, project or ""

    def record_success(self, name: str, latency_ms: float, tenant: str, project: Optional[str]) -> None:
        with self._lock:
            stat = self._stats.setdefault(name, TransportStats())
            stat.success += 1
            stat.latency_ms_total += latency_ms
            stat.latency_ms_last = latency_ms
            stat.last_error = None
            key = self._scope_key(tenant, project)
            scope_stat = stat.scopes.setdefault(key, ScopeStats())
            scope_stat.success += 1
            scope_stat.last_error = None
            scope_stat.last_latency_ms = latency_ms
        record_transport_success(name, tenant, project, latency_ms)

    def record_failure(self, name: str, error: str, tenant: str, project: Optional[str]) -> None:
        with self._lock:
            stat = self._stats.setdefault(name, TransportStats())
            stat.failure += 1
            stat.last_error = error
            key = self._scope_key(tenant, project)
            scope_stat = stat.scopes.setdefault(key, ScopeStats())
            scope_stat.failure += 1
            scope_stat.last_error = error
        record_transport_failure(name, tenant, project)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            data: Dict[str, Any] = {}
            for name, stat in self._stats.items():
                data[name] = {
                    "success": stat.success,
                    "failure": stat.failure,
                    "avg_latency_ms": round(stat.avg_latency_ms, 2),
                    "last_latency_ms": round(stat.latency_ms_last, 2),
                    "last_error": stat.last_error,
                    "scopes": [
                        {
                            "tenant": tenant,
                            "project": project or None,
                            "success": scope_stat.success,
                            "failure": scope_stat.failure,
                            "last_latency_ms": round(scope_stat.last_latency_ms, 2),
                            "last_error": scope_stat.last_error,
                        }
                        for (tenant, project), scope_stat in stat.scopes.items()
                    ],
                }
            return data


class RateLimiter:
    def __init__(self, limit_per_minute: int):
        self.limit = limit_per_minute
        self._window = deque()

    def allow(self) -> bool:
        now = time.time()
        window = self._window
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= self.limit:
            return False
        window.append(now)
        return True


class TransportBroker:
    def __init__(
        self,
        transports: Dict[str, Transport],
        cooldown_seconds: float = 2.0,
        transport_config: Optional[TransportConfig] = None,
    ):
        self.transports = transports
        self.failures: Dict[str, int] = {}
        self.cooldowns: Dict[str, float] = {}
        self.cooldown_seconds = cooldown_seconds
        self.metrics = TransportMetrics()
        self.config = transport_config or TransportConfig.load_default()
        self.rate_limiters: Dict[Tuple[str, str, str], RateLimiter] = {}

    @classmethod
    def default(cls) -> "TransportBroker":
        config = TransportConfig.load_default()
        return cls(
            transports={
                "openai": OpenAITransport(),
                "anthropic": AnthropicTransport(),
                "gemini": GeminiTransport(),
            },
            transport_config=config,
        )

    def inject(self, patch: Dict[str, Any], preferred: str = "best", scope: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        order = self._route_order(preferred)
        errors = []
        scope = scope or {}
        tenant = scope.get("tenant", "default")
        project = scope.get("project")
        for name in order:
            transport = self.transports.get(name)
            if not transport:
                continue
            if name in self.cooldowns and self.cooldowns[name] > time.time():
                continue
            if not self._check_quota(tenant, project, name):
                errors.append({"transport": name, "error": "rate limit exceeded", "latency_ms": 0.0})
                continue
            credentials = self.config.credentials(tenant, project, name) if self.config else None
            start = time.perf_counter()
            try:
                ack = transport.send(patch, credentials=credentials)
                latency_ms = (time.perf_counter() - start) * 1000
                self.metrics.record_success(name, latency_ms, tenant, project)
                return {"transport": name, "ack": ack, "latency_ms": round(latency_ms, 2)}
            except Exception as exc:  # pragma: no cover - network/availability dependent
                latency_ms = (time.perf_counter() - start) * 1000
                error_str = str(exc)
                self.metrics.record_failure(name, error_str, tenant, project)
                self.failures[name] = self.failures.get(name, 0) + 1
                self.cooldowns[name] = time.time() + self.cooldown_seconds
                errors.append({"transport": name, "error": error_str, "latency_ms": round(latency_ms, 2)})
        raise RuntimeError(f"All transports failed: {errors}")

    def _route_order(self, preferred: str) -> List[str]:
        if preferred == "best":
            return list(self.transports.keys())
        return [preferred] + [name for name in self.transports if name != preferred]

    def set_availability(self, name: str, available: bool) -> bool:
        transport = self.transports.get(name)
        if not transport or not isinstance(transport, BaseTransport):
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
            "metrics": self.metrics.snapshot(),
        }

    def metrics_snapshot(self) -> Dict[str, Any]:
        return self.metrics.snapshot()
    
    def health(self) -> Dict[str, Any]:
        now = time.time()
        metrics = self.metrics.snapshot()
        transports_info: List[Dict[str, Any]] = []
        for name, transport in self.transports.items():
            transports_info.append(
                {
                    "name": name,
                    "available": getattr(transport, "available", True),
                    "failures": self.failures.get(name, 0),
                    "cooldown_seconds": max(self.cooldowns.get(name, 0) - now, 0.0),
                    "metrics": metrics.get(name, {}),
                }
            )
        status = "ok"
        if any((not info["available"]) or info["failures"] > 0 for info in transports_info):
            status = "degraded"
        if not transports_info:
            status = "unknown"
        return {
            "status": status,
            "transports": transports_info,
            "config": self.config.summary() if self.config else {},
        }

    def _check_quota(self, tenant: str, project: Optional[str], transport_name: str) -> bool:
        if not self.config:
            return True
        limit = self.config.rate_limit(tenant, project, transport_name)
        if not limit:
            return True
        key = (tenant, project or "", transport_name)
        limiter = self.rate_limiters.get(key)
        if not limiter or limiter.limit != limit:
            limiter = RateLimiter(limit)
            self.rate_limiters[key] = limiter
        return limiter.allow()


def flatten_blueprint(blueprint: Dict[str, Any]) -> str:
    slots = blueprint.get("slots", [])
    parts = []
    for slot in slots:
        name = slot.get("name")
        content = slot.get("content")
        if content:
            parts.append(f"[{name}] {content}")
    return "\n\n".join(parts)
