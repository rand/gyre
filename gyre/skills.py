from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class SkillRegistry:
    def __init__(self, path: Path | None = None):
        self.path = path or Path("data") / "skills.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.skills: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            self.skills = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self.skills = {}

    def _persist(self) -> None:
        self.path.write_text(json.dumps(self.skills, indent=2), encoding="utf-8")

    def sync(self, promoted_skills: Dict[str, Any]) -> int:
        updated = 0
        for skill_id, payload in promoted_skills.items():
            entry = self.skills.setdefault(skill_id, {"skill": {}, "cohorts": []})
            entry["skill"] = payload
            updated += 1
        if updated:
            self._persist()
        return updated

    def share(self, skill_id: str, cohort: str) -> bool:
        entry = self.skills.get(skill_id)
        if not entry:
            return False
        cohorts = entry.setdefault("cohorts", [])
        if cohort not in cohorts:
            cohorts.append(cohort)
            self._persist()
        return True

    def list(self, cohort: str | None = None) -> List[Dict[str, Any]]:
        results = []
        for skill_id, entry in self.skills.items():
            if cohort and cohort not in entry.get("cohorts", []):
                continue
            results.append({"id": skill_id, **entry})
        return results
