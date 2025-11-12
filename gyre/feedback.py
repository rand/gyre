from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class FeedbackStore:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: Dict[str, Any]) -> Dict[str, Any]:
        entry = dict(record)
        entry["ts"] = datetime.now(timezone.utc).isoformat()
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        return entry

    def tail(self, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        items = lines[-limit:]
        return [json.loads(line) for line in items if line.strip()]

    def stats(self) -> Dict[str, int]:
        counts = {"accepted": 0, "rejected": 0}
        if not self.path.exists():
            return counts
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            verdict = (row.get("verdict") or "").lower()
            if verdict in counts:
                counts[verdict] += 1
        return counts

    def find(self, patch_id: str) -> Optional[Dict[str, Any]]:
        if not self.path.exists():
            return None
        for line in reversed(self.path.read_text(encoding="utf-8").splitlines()):
            data = json.loads(line)
            if data.get("patch_id") == patch_id:
                return data
        return None
