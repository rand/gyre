import dspy

class ObserveSession(dspy.Signature):
    """Infer task state and deltas from raw session IO."""
    task_desc: str
    events_json: str
    session_state_json: str

class ProposePatches(dspy.Signature):
    """Generate candidate patches from session state and graph neighborhood."""
    task_desc: str
    session_state_json: str
    neighborhood_json: str
    slot_specs_json: str
    patches_json: str

class RankCandidates(dspy.Signature):
    """Select and order items that maximize task utility per token."""
    task_desc: str
    budget_tokens: int
    items_json: str
    topk: int
    ranked_ids_json: str

class SummarizeForSlot(dspy.Signature):
    """Summarize items for a slot with budget and citation anchors."""
    slot_name: str
    max_tokens: int
    items_with_citations_json: str
    summary_text: str
    kept_citations_json: str

class EVofDeferredQuery(dspy.Signature):
    """Predict EV and cost of executing a deferred query given task and history."""
    task_desc: str
    query_plan_json: str
    ev_score: float

class RedactForScope(dspy.Signature):
    """Redact sensitive fields; output diff against original."""
    target_scope: str
    draft_json: str
    policy_json: str
    redacted_json: str

class BlueprintFill(dspy.Signature):
    """Produce a structured context blueprint with slot caps respected."""
    task_desc: str
    slot_specs_json: str
    fragments_json: str
    blueprint_json: str
