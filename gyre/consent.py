from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


@dataclass
class ConsentRegistry:
    path: Path
    consents: Dict[str, bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.consents.update(json.loads(self.path.read_text(encoding="utf-8")))

    def key(self, tenant: str, project: str, user: str) -> str:
        return f"{tenant}:{project}:{user}"

    def grant(self, tenant: str, project: str, user: str, consent: bool) -> None:
        self.consents[self.key(tenant, project, user)] = consent
        self.path.write_text(json.dumps(self.consents, indent=2), encoding="utf-8")

    def has_consent(self, tenant: str, project: str, user: str) -> bool:
        return self.consents.get(self.key(tenant, project, user), False)

    def list_all(self) -> Dict[str, bool]:
        return dict(self.consents)
