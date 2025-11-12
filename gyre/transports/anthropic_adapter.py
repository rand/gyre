from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from .errors import TransportError


@dataclass
class AnthropicConfig:
    api_key: Optional[str]
    base_url: str = "https://api.anthropic.com"
    model: str = "claude-3-5-sonnet-latest"
    timeout: float = 10.0
    max_retries: int = 2
    force_stub: bool = False

    @classmethod
    def from_env(cls) -> "AnthropicConfig":
        return cls(
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
            base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
            model=os.environ.get("ANTHROPIC_TRANSPORT_MODEL", "claude-3-5-sonnet-latest"),
            timeout=float(os.environ.get("ANTHROPIC_TRANSPORT_TIMEOUT", "10")),
            max_retries=int(os.environ.get("ANTHROPIC_TRANSPORT_MAX_RETRIES", "2")),
            force_stub=os.environ.get("GYRE_TRANSPORT_FORCE_STUB", "0") == "1",
        )

    @property
    def is_stub(self) -> bool:
        return self.force_stub or not self.api_key

    def override(self, data: Optional[Dict[str, Any]]) -> "AnthropicConfig":
        if not data:
            return self
        return AnthropicConfig(
            api_key=data.get("api_key", self.api_key),
            base_url=data.get("base_url", self.base_url),
            model=data.get("model", self.model),
            timeout=float(data.get("timeout", self.timeout)),
            max_retries=int(data.get("max_retries", self.max_retries)),
            force_stub=data.get("force_stub", self.force_stub),
        )


class AnthropicClient:
    def __init__(self, config: Optional[AnthropicConfig] = None):
        self.config = config or AnthropicConfig.from_env()

    def inject_message(self, session_id: str, text: str, *, credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        config = self.config.override(credentials)
        if config.is_stub:
            return {
                "mode": "stub",
                "session_id": session_id,
                "method": "message",
                "payload": text,
            }
        headers = {
            "x-api-key": config.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": config.model,
            "max_tokens": 32,
            "messages": [
                {"role": "user", "content": f"Attach this context to session {session_id}:\n{text}"}
            ],
        }
        url = f"{config.base_url.rstrip('/')}/v1/messages"
        last_error = None
        for attempt in range(config.max_retries + 1):
            try:
                resp = httpx.post(url, headers=headers, json=payload, timeout=config.timeout)
                resp.raise_for_status()
                data = resp.json()
                return {"mode": "live", "id": data.get("id"), "status": resp.status_code}
            except httpx.HTTPError as exc:  # pragma: no cover - network dependent
                last_error = str(exc)
                time.sleep(min(2 ** attempt * 0.2, 1.0))
        raise TransportError("anthropic", last_error or "unknown error")
