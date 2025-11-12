from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


DEFAULT_SCOPE = {"tenant": "demo", "project": "demo"}


@dataclass
class SessionRegistry:
    scopes: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def register(self, session_id: str, *, tenant: str, project: str, user: str) -> Dict[str, str]:
        scope = {"tenant": tenant, "project": project, "user": user}
        self.scopes[session_id] = scope
        return scope

    def get(self, session_id: str, user: Optional[str] = None) -> Dict[str, str]:
        if session_id in self.scopes:
            return self.scopes[session_id]
        scope = {
            "tenant": DEFAULT_SCOPE["tenant"],
            "project": DEFAULT_SCOPE["project"],
            "user": user or session_id,
        }
        self.scopes[session_id] = scope
        return scope

