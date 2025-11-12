from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def summarize_propose_logs(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"entries": 0}
    entries = 0
    stage_a_tokens = 0
    stage_b_tokens = 0
    selected = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        entries += 1
        stage_a = entry.get("stage_a", {})
        selection = entry.get("selection", {})
        stage_a_tokens += stage_a.get("ledger", {}).get("tokens_used", 0)
        stage_b_tokens += selection.get("ledger", {}).get("tokens_used", 0)
        selected += len(selection.get("selected", []))
    if not entries:
        return {"entries": 0}
    return {
        "entries": entries,
        "avg_stage_a_tokens": stage_a_tokens / entries,
        "avg_stage_b_tokens": stage_b_tokens / entries,
        "avg_selected": selected / entries,
    }
