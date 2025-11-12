from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from .errors import TransportError


@dataclass
class OpenAIConfig:
    api_key: Optional[str]
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    timeout: float = 10.0
    max_retries: int = 2
    force_stub: bool = False

    @classmethod
    def from_env(cls) -> "OpenAIConfig":
        return cls(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=os.environ.get("OPENAI_TRANSPORT_MODEL", "gpt-4o-mini"),
            timeout=float(os.environ.get("OPENAI_TRANSPORT_TIMEOUT", "10")),
            max_retries=int(os.environ.get("OPENAI_TRANSPORT_MAX_RETRIES", "2")),
            force_stub=os.environ.get("GYRE_TRANSPORT_FORCE_STUB", "0") == "1",
        )

    @property
    def is_stub(self) -> bool:
        return self.force_stub or not self.api_key

    def override(self, data: Optional[Dict[str, Any]]) -> "OpenAIConfig":
        if not data:
            return self
        return OpenAIConfig(
            api_key=data.get("api_key", self.api_key),
            base_url=data.get("base_url", self.base_url),
            model=data.get("model", self.model),
            timeout=float(data.get("timeout", self.timeout)),
            max_retries=int(data.get("max_retries", self.max_retries)),
            force_stub=data.get("force_stub", self.force_stub),
        )


class OpenAIClient:
    def __init__(self, config: Optional[OpenAIConfig] = None):
        self.config = config or OpenAIConfig.from_env()

    def send_system_prefix(self, session_id: str, text: str, *, credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        config = self.config.override(credentials)
        if config.is_stub:
            return {
                "mode": "stub",
                "session_id": session_id,
                "method": "system_prefix",
                "payload": text,
            }
        payload = {
            "model": config.model,
            "input": [
                {
                    "role": "developer",
                    "content": [
                        {"type": "text", "text": f"Context patch for session {session_id}:\n{text}"}
                    ],
                }
            ],
        }
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{config.base_url.rstrip('/')}/responses"
        last_error = None
        for attempt in range(config.max_retries + 1):
            try:
                resp = httpx.post(url, headers=headers, json=payload, timeout=config.timeout)
                resp.raise_for_status()
                data = resp.json()
                return {
                    "mode": "live",
                    "response_id": data.get("id"),
                    "status": resp.status_code,
                }
            except httpx.HTTPError as exc:  # pragma: no cover - network dependent
                last_error = str(exc)
                time.sleep(min(2 ** attempt * 0.2, 1.0))
        raise TransportError("openai", last_error or "unknown error")
