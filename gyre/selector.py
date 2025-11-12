import logging
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


def mmr_diversity_score(item, chosen):
    src = item.get("source")
    if not src:
        return 0.0
    if any(c.get("source") == src for c in chosen):
        return -0.2
    return 0.0


def utility(item, weights):
    f = item.get("features", {})
    costs = item.get("costs", {})
    risk = item.get("risks", {})
    return (
        weights["relevance"] * f.get("relevance", 0.0)
        + weights["actionability"] * f.get("actionability", 0.0)
        + weights["freshness"] * f.get("freshness", 0.0)
        + weights["importance"] * f.get("importance", 0.0)
        + weights["reliability"] * f.get("reliability", 0.0)
        - weights["cost"] * (costs.get("tokens_est", 0) / 1000.0)
        - weights["sensitivity"] * risk.get("leakage", 0.0)
    )


@dataclass
class SelectionLedger:
    tokens_cap: int
    latency_cap: int
    risk_cap: str
    tokens_used: int = 0
    latency_ms_used: int = 0
    selected: int = 0
    rejected: int = 0

    def can_fit(self, item: Dict[str, Any]) -> bool:
        t = item.get("costs", {}).get("tokens_est", 0)
        l = item.get("costs", {}).get("latency_est_ms", 0)
        if self.tokens_used + t > self.tokens_cap:
            return False
        if self.latency_ms_used + l > self.latency_cap:
            return False
        return True

    def within_risk(self, item: Dict[str, Any]) -> bool:
        label = item.get("risks", {}).get("sensitivity", "low")
        return RISK_ORDER.get(label, 2) <= RISK_ORDER.get(self.risk_cap, 1)

    def consume(self, item: Dict[str, Any]) -> None:
        self.tokens_used += item.get("costs", {}).get("tokens_est", 0)
        self.latency_ms_used += item.get("costs", {}).get("latency_est_ms", 0)
        self.selected += 1

    def reject(self) -> None:
        self.rejected += 1

    def asdict(self) -> Dict[str, Any]:
        return asdict(self)


DEFAULT_WEIGHTS = {
    "relevance": 1.0,
    "actionability": 1.0,
    "freshness": 0.6,
    "importance": 0.5,
    "reliability": 0.4,
    "cost": 0.3,
    "sensitivity": 0.4,
}


def select(
    candidates: List[Dict[str, Any]],
    budgets: Dict[str, int],
    *,
    task_desc: str = "",
    risk_cap: str = "low",
    weights: Optional[Dict[str, float]] = None,
    ranker: Optional[Any] = None,
    rank_weight: float = 0.4,
) -> Dict[str, Any]:
    ledger = SelectionLedger(
        tokens_cap=budgets.get("tokens", 800),
        latency_cap=budgets.get("latency_ms", 800),
        risk_cap=risk_cap,
    )
    weights = weights or DEFAULT_WEIGHTS

    chosen: List[Dict[str, Any]] = []
    trace: List[Dict[str, Any]] = []
    remaining = candidates[:]
    ranking: List[str] = []
    ranking_meta: Optional[Dict[str, Any]] = None
    if ranker:
        try:
            if hasattr(ranker, "rank"):
                ranking, ranking_meta = ranker.rank(task_desc, budgets, candidates)
            else:
                ranking, ranking_meta = ranker(task_desc, budgets, candidates)
        except AttributeError:
            ranking, ranking_meta = ranker(task_desc, budgets, candidates)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Ranker failed; continuing without DSPy order: %s", exc)
            ranking = []
            ranking_meta = {"mode": "error", "error": str(exc)}
    order = {cid: idx for idx, cid in enumerate(ranking)}
    order_size = max(1, len(order))

    while remaining:
        best = None
        best_gain = -1e9
        best_rank_bonus = 0.0
        for item in remaining:
            if not ledger.can_fit(item):
                continue
            if not ledger.within_risk(item):
                continue
            rank_bonus = 0.0
            if order:
                pos = order.get(item.get("id"))
                if pos is not None:
                    rank_bonus = (order_size - pos) / order_size
            gain = utility(item, weights) + mmr_diversity_score(item, chosen) + rank_weight * rank_bonus
            if gain > best_gain:
                best_gain, best = gain, item
                best_rank_bonus = rank_bonus
        if best is None:
            break
        chosen.append(best)
        ledger.consume(best)
        trace.append(
            {
                "id": best.get("id"),
                "gain": round(best_gain, 3),
                "tokens": best.get("costs", {}).get("tokens_est", 0),
                "latency": best.get("costs", {}).get("latency_est_ms", 0),
                "rank_bonus": round(best_rank_bonus * rank_weight, 3),
            }
        )
        remaining.remove(best)

    ledger.rejected = len(candidates) - len(chosen)
    result: Dict[str, Any] = {
        "selected": chosen,
        "ledger": ledger.asdict(),
        "trace": trace,
    }
    if ranking_meta:
        result["ranker"] = ranking_meta
    return result
