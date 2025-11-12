from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Tuple

from gyre import programs


class DSPYRanker:
    """Bridges the compiled DSPy ranker into Stage-B selection."""

    def __init__(self, *, max_items: int = 50):
        self.max_items = max_items
        self._logger = logging.getLogger(__name__)

    def rank(
        self,
        task_desc: str,
        budgets: Dict[str, int],
        candidates: List[Dict[str, Any]],
        topk: int | None = None,
    ) -> Tuple[List[str], Dict[str, Any]]:
        journal: Dict[str, Any] = {
            "max_items": self.max_items,
            "request": {
                "task_desc": task_desc[:512],
                "budget_tokens": int(budgets.get("tokens", 0)),
                "topk": topk or min(self.max_items, len(candidates)),
            },
        }
        if not task_desc or not candidates:
            journal["mode"] = "empty"
            journal["response"] = {"ids": []}
            return [], journal

        limited = candidates[: self.max_items]
        items_payload = [self._simplify_item(item) for item in limited]
        journal["request"]["items"] = items_payload

        start = time.perf_counter()
        try:
            prediction = programs.ranker(
                task_desc=task_desc,
                budget_tokens=journal["request"]["budget_tokens"],
                items_json=json.dumps(items_payload),
                topk=journal["request"]["topk"],
            )
            ranked_ids = self._parse_ids(getattr(prediction, "ranked_ids_json", None))
            latency_ms = int((time.perf_counter() - start) * 1000)
            if not ranked_ids:
                ranked_ids = self._fallback_ids(limited)
                mode = "fallback"
            else:
                mode = "dspy"
            journal["mode"] = mode
            journal["response"] = {"ids": ranked_ids, "latency_ms": latency_ms}
            return ranked_ids, journal
        except Exception as exc:  # pragma: no cover - logged + fallback
            latency_ms = int((time.perf_counter() - start) * 1000)
            self._logger.debug("DSPy ranker failed; falling back: %s", exc)
            ranked_ids = self._fallback_ids(limited)
            journal["mode"] = "fallback"
            journal["response"] = {
                "ids": ranked_ids,
                "latency_ms": latency_ms,
                "error": str(exc),
            }
            return ranked_ids, journal

    def _simplify_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        content = item.get("content", {})
        text = ""
        if isinstance(content, dict):
            text = (
                content.get("text")
                or content.get("body")
                or content.get("message")
                or ""
            )
        elif content:
            text = str(content)
        text = text[:512]
        return {
            "id": item.get("id"),
            "kind": item.get("kind"),
            "source": item.get("source"),
            "features": item.get("features", {}),
            "costs": item.get("costs", {}),
            "risks": item.get("risks", {}),
            "text": text,
        }

    def _parse_ids(self, raw: Any) -> List[str]:
        if not raw:
            return []
        if isinstance(raw, list):
            return [str(item) for item in raw if item]
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed if item]
            except json.JSONDecodeError:
                parts = [part.strip() for part in raw.split(",")]
                return [part for part in parts if part]
        return []

    def _fallback_ids(self, candidates: List[Dict[str, Any]]) -> List[str]:
        scored = sorted(
            (
                (self._score(item), item.get("id"))
                for item in candidates
                if item.get("id")
            ),
            reverse=True,
        )
        return [cid for _score, cid in scored if cid]

    def _score(self, item: Dict[str, Any]) -> float:
        features = item.get("features", {})
        costs = item.get("costs", {})
        return (
            0.7 * features.get("relevance", 0.0)
            + 0.5 * features.get("actionability", 0.0)
            + 0.3 * features.get("freshness", 0.0)
            + 0.2 * features.get("importance", 0.0)
            - 0.1 * (costs.get("tokens_est", 0) / 1000.0)
        )
