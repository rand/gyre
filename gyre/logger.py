from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class DatasetLogger:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log_propose(
        self,
        payload: Any,
        stage_a: Dict[str, Any],
        selection: Dict[str, Any],
        patch: Dict[str, Any],
        *,
        pool: List[Dict[str, Any]] | None = None,
    ) -> None:
        payload_dict = _to_dict(payload)
        entry = {
            "task_desc": payload_dict.get("task_desc"),
            "session_id": payload_dict.get("session_id"),
            "budgets": payload_dict.get("budgets", {}),
            "stage_a": stage_a,
            "selection": selection,
            "patch": patch,
        }
        if pool is not None:
            entry["pool"] = pool
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")


def _to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, dict):
        return obj
    return getattr(obj, "__dict__", {})
