from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


class FeatureFlags:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.flags: Dict[str, bool] = {
            "dspy_logging": True,
            "dspy_injection": False,
            "dspy_selection": False,
        }
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                self.flags.update(json.loads(self.path.read_text(encoding="utf-8")))
            except Exception:
                pass

    def _save(self):
        self.path.write_text(json.dumps(self.flags, indent=2), encoding="utf-8")

    def is_enabled(self, name: str) -> bool:
        return self.flags.get(name, False)

    def set(self, name: str, value: bool):
        self.flags[name] = value
        self._save()

    def all(self) -> Dict[str, bool]:
        return dict(self.flags)
