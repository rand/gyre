from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Metrics:
    _lock: threading.Lock = field(default_factory=threading.Lock)
    totals: Dict[str, int] = field(default_factory=dict)
    latest_observe: Dict[str, Any] = field(default_factory=dict)

    def incr(self, key: str, amount: int = 1) -> None:
        with self._lock:
            self.totals[key] = self.totals.get(key, 0) + amount

    def record_observe(
        self,
        *,
        session_id: str,
        events_count: int,
        novel_events: int,
        novelty_score: float,
        tokens_est: int,
    ) -> None:
        with self._lock:
            self.totals["ingest_calls"] = self.totals.get("ingest_calls", 0) + 1
            self.totals["events_processed"] = self.totals.get("events_processed", 0) + events_count
            self.totals["novel_events"] = self.totals.get("novel_events", 0) + novel_events
            self.totals["tokens_observed"] = self.totals.get("tokens_observed", 0) + tokens_est
            self.latest_observe = {
                "session_id": session_id,
                "events_count": events_count,
                "novel_events": novel_events,
                "novelty_score": novelty_score,
                "tokens_est": tokens_est,
            }

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "totals": dict(self.totals),
                "latest_observe": dict(self.latest_observe),
            }


METRICS = Metrics()
