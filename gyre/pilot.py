from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


class PilotRollout:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else None
        self.rules: Dict[str, Any] = {}
        if self.path and self.path.exists():
            try:
                self.rules = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.rules = {}

    def is_enabled(self) -> bool:
        return bool(self.rules)

    def _default_allow(self) -> bool:
        defaults = self.rules.get("defaults", {})
        return bool(defaults.get("allow", True))

    def is_allowed(self, scope: Dict[str, str]) -> Tuple[bool, Optional[str]]:
        if not self.rules:
            return True, None
        tenant = scope.get("tenant", "default")
        project = scope.get("project")
        allowed = self._default_allow()
        message: Optional[str] = None

        tenant_cfg = self.rules.get("tenants", {}).get(tenant)
        if tenant_cfg:
            allowed = tenant_cfg.get("allow", allowed)
            message = tenant_cfg.get("message")
            if project:
                project_cfg = tenant_cfg.get("projects", {}).get(project)
                if project_cfg is not None:
                    allowed = project_cfg.get("allow", allowed)
                    message = project_cfg.get("message", message)
        return bool(allowed), message
