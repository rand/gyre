from __future__ import annotations

import itertools
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol


class QueryProvider(Protocol):
    name: str

    def propose(self, task_desc: str) -> List["QueryPlan"]:
        ...

    def execute(self, plan: "QueryPlan", task_desc: str) -> Dict[str, Any]:
        ...


@dataclass
class QueryPlan:
    provider: str
    query: str
    pattern: str
    expected_value: float
    tokens_est: int
    latency_est_ms: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_candidate(self, session_id: str) -> Dict[str, Any]:
        return {
            "id": f"deferred:{session_id}:{self.provider}:{uuid.uuid4().hex[:8]}",
            "kind": "deferred_query",
            "status": "deferred",
            "session_id": session_id,
            "content": {
                "query": self.query,
                "provider": self.provider,
                "pattern": self.pattern,
                "metadata": self.metadata,
            },
            "features": {
                "expected_value": round(self.expected_value, 3),
                "relevance": min(1.0, 0.3 + self.expected_value / 2),
                "freshness": 1.0,
            },
            "costs": {
                "tokens_est": self.tokens_est,
                "latency_est_ms": self.latency_est_ms,
            },
            "risks": {"sensitivity": "low"},
            "source": f"planner:{self.provider}",
        }


@dataclass
class StaticProvider:
    name: str
    pattern: str
    query_template: str
    token_cost: int
    latency_cost: int
    base_ev: float
    response: str

    def propose(self, task_desc: str) -> List[QueryPlan]:
        ev = self.base_ev
        if self.pattern.lower() in task_desc.lower():
            ev = min(1.0, self.base_ev + 0.3)
        return [
            QueryPlan(
                provider=self.name,
                query=self.query_template.format(task=task_desc),
                pattern=self.pattern,
                expected_value=ev,
                tokens_est=self.token_cost,
                latency_est_ms=self.latency_cost,
            )
        ]

    def execute(self, plan: QueryPlan, task_desc: str) -> Dict[str, Any]:
        return {
            "text": self.response.format(task=task_desc, provider=self.name),
            "query": plan.query,
            "provider": self.name,
        }


class DeferredQueryPlanner:
    def __init__(self, providers: List[QueryProvider]):
        self.providers = providers

    @classmethod
    def default(cls) -> "DeferredQueryPlanner":
        providers: List[QueryProvider] = [
            StaticProvider(
                name="parts_api",
                pattern="parts",
                query_template="fetch parts recommendations for {task}",
                token_cost=150,
                latency_cost=120,
                base_ev=0.6,
                response="Parts catalog suggests coil springs kit for {task}.",
            ),
            StaticProvider(
                name="status",
                pattern="monitor",
                query_template="check latest incidents for {task}",
                token_cost=80,
                latency_cost=70,
                base_ev=0.4,
                response="Status dashboard: no blocking incidents for {task}.",
            ),
            StaticProvider(
                name="kb",
                pattern="plan",
                query_template="retrieve constraints for {task}",
                token_cost=90,
                latency_cost=60,
                base_ev=0.5,
                response="Knowledge base snippet for {task}.",
            ),
        ]
        return cls(providers)

    def run(self, task_desc: str, budgets: Dict[str, int], session_id: str) -> Dict[str, Any]:
        plans = list(self._propose_plans(task_desc))
        latency_cap = budgets.get("latency_ms", 800)
        tokens_cap = budgets.get("tokens", 800)

        selected: List[QueryPlan] = []
        ledger = {"latency_ms_used": 0, "tokens_used": 0, "queries_considered": len(plans)}
        for plan in sorted(plans, key=self._score, reverse=True):
            lat = plan.latency_est_ms
            tok = plan.tokens_est
            if ledger["latency_ms_used"] + lat > latency_cap:
                continue
            if ledger["tokens_used"] + tok > tokens_cap:
                continue
            selected.append(plan)
            ledger["latency_ms_used"] += lat
            ledger["tokens_used"] += tok

        deferred_candidates = [plan.to_candidate(session_id) for plan in plans]
        executed_candidates: List[Dict[str, Any]] = []
        for plan in selected:
            provider = self._provider_by_name(plan.provider)
            payload = provider.execute(plan, task_desc)
            executed_candidates.append(
                {
                    "id": f"tool:{session_id}:{plan.provider}:{uuid.uuid4().hex[:8]}",
                    "kind": "tool_result",
                    "session_id": session_id,
                    "content": payload,
                    "features": {
                        "relevance": min(1.0, 0.5 + plan.expected_value / 2),
                        "actionability": 0.6,
                    },
                    "costs": {"tokens_est": plan.tokens_est, "latency_est_ms": plan.latency_est_ms},
                    "source": plan.provider,
                }
            )

        return {
            "deferred": deferred_candidates,
            "executed": executed_candidates,
            "ledger": ledger,
        }

    def _propose_plans(self, task_desc: str) -> List[QueryPlan]:
        plans: List[QueryPlan] = []
        for provider in self.providers:
            plans.extend(provider.propose(task_desc))
        for plan, counter in zip(plans, itertools.count()):
            plan.metadata["rank"] = counter
        return plans

    def _score(self, plan: QueryPlan) -> float:
        return plan.expected_value / max(1, plan.latency_est_ms)

    def _provider_by_name(self, name: str) -> QueryProvider:
        for provider in self.providers:
            if provider.name == name:
                return provider
        raise ValueError(f"No provider named {name}")
