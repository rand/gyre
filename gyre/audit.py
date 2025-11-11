from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class AuditLog:
    path: Path
    entries: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.entries.extend(json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line)

    def append(self, record: Dict[str, Any]) -> None:
        self.entries.append(record)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    def tail(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.entries[-limit:]
