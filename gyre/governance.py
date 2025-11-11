from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict

SENSITIVE_KEYS = {"email", "ssn", "credit_card", "api_key", "token"}
RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


def redact(draft: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    def traverse(obj: Any) -> Any:
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                if k in SENSITIVE_KEYS:
                    result[k] = "***"
                else:
                    result[k] = traverse(v)
            return result
        if isinstance(obj, list):
            return [traverse(item) for item in obj]
        return obj

    return traverse(draft)


@dataclass
class PolicyPack:
    sensitivity: str = "medium"
    max_tokens: int = 1200

    def allows(self, patch: Dict[str, Any]) -> bool:
        ledger = patch.get("budget", {})
        return ledger.get("tokens_used", ledger.get("max_tokens", 0)) <= self.max_tokens


class PolicyEngine:
    def __init__(self, default_pack: PolicyPack | None = None):
        self.default_pack = default_pack or PolicyPack()

    def evaluate(self, patch: Dict[str, Any], scope: Dict[str, str]) -> Dict[str, Any]:
        allowed = self.default_pack.allows(patch)
        result = {
            "allowed": allowed,
            "reason": None if allowed else "token budget exceeded",
            "scope": scope,
        }
        return result


def risk_ok(risk_label: str, cap: str) -> bool:
    return RISK_ORDER.get(risk_label, 2) <= RISK_ORDER.get(cap, 1)
