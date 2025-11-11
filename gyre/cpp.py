from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class Patch:
    id: str
    task_id: str
    target_session_id: str
    ttl_ms: int
    slot: str  # task_header|constraints|user_prefs|retrieved_evidence|tool_args|citations
    body: Any  # text or structured payload
    budget: Dict[str, int]  # max_tokens, max_latency_ms
    policy: Dict[str, Any]  # allowed_scopes, sensitivity_max
    provenance: List[Dict[str, str]] = field(default_factory=list)

@dataclass
class BudgetLedger:
    tokens_used: int = 0
    tokens_cap: int = 0
    latency_ms_used: int = 0
    latency_ms_cap: int = 0

BLUEPRINT_SLOTS = [
    "task_header", "constraints", "user_prefs", "retrieved_evidence", "tool_args", "citations"
]
