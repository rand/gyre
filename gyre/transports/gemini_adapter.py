from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from .errors import TransportError


@dataclass
class GeminiConfig:
    api_key: Optional[str]
    base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    model: str = "models/gemini-1.5-flash"
    timeout: float = 10.0
    max_retries: int = 2
    force_stub: bool = False

    @classmethod
    def from_env(cls) -> "GeminiConfig":
        return cls(
            api_key=os.environ.get("GEMINI_API_KEY"),
            base_url=os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"),
            model=os.environ.get("GEMINI_TRANSPORT_MODEL", "models/gemini-1.5-flash"),
            timeout=float(os.environ.get("GEMINI_TRANSPORT_TIMEOUT", "10")),
            max_retries=int(os.environ.get("GEMINI_TRANSPORT_MAX_RETRIES", "2")),
            force_stub=os.environ.get("GYRE_TRANSPORT_FORCE_STUB", "0") == "1",
        )

    @property
    def is_stub(self) -> bool:
        return self.force_stub or not self.api_key

    def override(self, data: Optional[Dict[str, Any]]) -> "GeminiConfig":
        if not data:
            return self
        return GeminiConfig(
            api_key=data.get("api_key", self.api_key),
            base_url=data.get("base_url", self.base_url),
            model=data.get("model", self.model),
            timeout=float(data.get("timeout", self.timeout)),
            max_retries=int(data.get("max_retries", self.max_retries)),
            force_stub=data.get("force_stub", self.force_stub),
        )


class GeminiClient:
    def __init__(self, config: Optional[GeminiConfig] = None):
        self.config = config or GeminiConfig.from_env()

    def inject_function_result(self, session_id: str, name: str, result: Dict[str, Any], *, credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        config = self.config.override(credentials)
        if config.is_stub:
            return {
                "mode": "stub",
                "session_id": session_id,
                "method": "function_result",
                "name": name,
                "payload": result,
            }
        url = f"{config.base_url.rstrip('/')}/{config.model}:generateContent?key={config.api_key}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": f"Inject function {name} for session {session_id} with payload:\n{result}"
                        }
                    ],
                }
            ]
        }
        last_error = None
        for attempt in range(config.max_retries + 1):
            try:
                resp = httpx.post(url, json=payload, timeout=config.timeout)
                resp.raise_for_status()
                data = resp.json()
                return {"mode": "live", "candidates": len(data.get("candidates", [])), "status": resp.status_code}
            except httpx.HTTPError as exc:  # pragma: no cover - network dependent
                last_error = str(exc)
                time.sleep(min(2 ** attempt * 0.2, 1.0))
        raise TransportError("gemini", last_error or "unknown error")
