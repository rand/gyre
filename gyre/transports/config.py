from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class TransportEntry:
    data: Dict[str, Any]

    def credentials(self) -> Dict[str, Any]:
        fields = ["api_key", "base_url", "model", "timeout", "max_retries", "force_stub"]
        return {k: self.data[k] for k in fields if k in self.data}

    def quota(self) -> Optional[int]:
        rate = self.data.get("rate_limit_per_min") or self.data.get("max_requests_per_min")
        return int(rate) if rate else None


class TransportConfig:
    def __init__(self, path: Optional[Path] = None, data: Optional[Dict[str, Any]] = None):
        self.path = path
        self._data = data or {}
        if self.path and self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self._data = {}

    @classmethod
    def load_default(cls) -> "TransportConfig":
        config_path = Path(__file__).resolve().parents[1] / "config" / "transports.json"
        return cls(config_path if config_path.exists() else None)

    def _lookup(self, tenant: str, project: Optional[str], transport: str) -> Optional[TransportEntry]:
        data = self._data or {}
        defaults = data.get("defaults", {})
        entry: Dict[str, Any] = dict(defaults.get(transport, {}))

        tenants = data.get("tenants", {})
        tenant_cfg = tenants.get(tenant, {})
        entry.update(tenant_cfg.get(transport, {}))

        if project:
            project_cfg = tenant_cfg.get("projects", {}).get(project, {})
            entry.update(project_cfg.get(transport, {}))

        return TransportEntry(entry) if entry else None

    def credentials(self, tenant: str, project: Optional[str], transport: str) -> Optional[Dict[str, Any]]:
        entry = self._lookup(tenant, project, transport)
        if not entry:
            return None
        creds = entry.credentials()
        return creds or None

    def rate_limit(self, tenant: str, project: Optional[str], transport: str) -> Optional[int]:
        entry = self._lookup(tenant, project, transport)
        return entry.quota() if entry else None
