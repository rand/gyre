from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import datetime as dt
from pathlib import Path

from gyre.observer import observe, infer_task_desc
from gyre.stores.private_store import PrivateStore
from gyre.stores.graph_store import TemporalGraph
from gyre.retriever import retrieve
from gyre.selector import select
from gyre.composer import compose
from gyre.governance import redact, PolicyEngine
from gyre.telemetry import METRICS
from gyre.planner import DeferredQueryPlanner
from gyre.transports.broker import TransportBroker
from gyre.audit import AuditLog
from gyre.consent import ConsentRegistry
from gyre.skills import SkillRegistry
from gyre.feature_flags import FeatureFlags
from gyre.logger import DatasetLogger
from gyre.metrics import summarize_propose_logs

app = FastAPI(title="Gyre Dev Server")
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PRIVATE = PrivateStore()
GRAPH = TemporalGraph()
PLANNER = DeferredQueryPlanner.default()
BROKER = TransportBroker.default()
POLICY = PolicyEngine()
AUDIT = AuditLog(DATA_DIR / "audit.log")
CONSENTS = ConsentRegistry(DATA_DIR / "consent.json")
SKILLS = SkillRegistry(DATA_DIR / "skills.json")
FLAGS = FeatureFlags(DATA_DIR / "feature_flags.json")
DATA_LOGGER = DatasetLogger(DATA_DIR / "logs/propose.jsonl")

def build_fragments(task_desc: str, chosen: List[Dict[str, Any]], executed_tools: List[Dict[str, Any]]) -> Dict[str, str]:
    evidence = []
    for item in chosen:
        text = item.get("content", {}).get("text")
        if text:
            evidence.append(text)
    for result in executed_tools:
        text = result.get("content", {}).get("text")
        if text:
            evidence.append(text)
    citations = []
    for item in chosen:
        for cite in item.get("provenance", []):
            if cite.get("cite"):
                citations.append(cite["cite"])
    return {
        "task_header": task_desc,
        "retrieved_evidence": "\n\n".join(evidence),
        "citations": "\n".join(citations),
    }

class Ingest(BaseModel):
    session_id: str
    events: List[Dict[str,Any]]

class Propose(BaseModel):
    session_id: str
    task_desc: str
    budgets: Dict[str,int]
    slot_specs: List[Dict[str,Any]]

class ManualExport(BaseModel):
    session_id: str
    candidate_ids: List[str]
    slot_specs: List[Dict[str,Any]]
    note: str | None = None

class InjectPatch(BaseModel):
    patch: Dict[str, Any]
    transport: str = "best"

class ConsentRequest(BaseModel):
    tenant: str
    project: str
    user: str
    consent: bool = True

class TransportChaosRequest(BaseModel):
    transport: str
    available: bool

class ShareSkillRequest(BaseModel):
    skill_id: str
    cohort: str

@app.post("/observe/ingest")
def ingest(payload: Ingest):
    task = infer_task_desc(payload.events)
    state = observe(task, payload.events)
    novel = state["novelty"]["novel_events"]
    summarized = (task or "\n".join(f"[{ev['kind']}] {ev['text']}" for ev in novel))[:500]
    tokens_est = max(1, len(summarized.split()))
    novelty_score = state["novelty"]["score"]
    timestamp = state["recent_events"][-1]["t"] if state["recent_events"] else ""
    cand = {
        "id": f"evt:{payload.session_id}:{len(PRIVATE.items)+1}",
        "kind": "episode",
        "content": {"text": summarized, "novel_events": novel},
        "source": f"session:{payload.session_id}",
        "timestamp": timestamp,
        "features": {
            "relevance": min(1.0, 0.4 + 0.6 * novelty_score),
            "actionability": min(1.0, 0.2 + 0.1 * len(state.get("entities", []))),
            "freshness": 1.0,
        },
        "costs": {"tokens_est": tokens_est, "latency_est_ms": 10},
        "risks": {"sensitivity": "low", "leakage": 0.0},
        "provenance": [
            {"cite": f"session://{payload.session_id}#{ev['t']}", "kind": ev["kind"]}
            for ev in novel
        ],
        "session_id": payload.session_id,
        "scope": {"tenant":"demo","project":"demo","user":payload.session_id},
        "graph": {"entities": state.get("entities",[]), "relations": []}
    }
    PRIVATE.upsert(cand)
    GRAPH.upsert_item(cand)
    METRICS.record_observe(
        session_id=payload.session_id,
        events_count=len(payload.events),
        novel_events=len(novel),
        novelty_score=novelty_score,
        tokens_est=tokens_est,
    )
    return {"ok": True, "state": state}

@app.post("/patches/propose")
def propose(p: Propose):
    plan = PLANNER.run(p.task_desc, p.budgets, p.session_id)
    executed_ids = []
    scope = {"tenant":"demo","project":"demo","user":p.session_id}
    for deferred in plan["deferred"]:
        deferred["scope"] = scope
        PRIVATE.upsert(deferred)
    for result in plan["executed"]:
        result["scope"] = scope
        PRIVATE.upsert(result)
        executed_ids.append(result["id"])
    pool = PRIVATE.query(limit=200)
    pool = retrieve(p.task_desc, pool)
    selection = select(pool, p.budgets, risk_cap=p.budgets.get("risk", "low"))
    chosen = selection["selected"]
    # Compose a tiny patch
    fragments = build_fragments(p.task_desc, chosen, plan["executed"])
    blueprint = compose(p.slot_specs, fragments)
    redacted = redact(blueprint, scope)
    patch = {
        "id": "patch-1", "task_id": "t-1", "target_session_id": p.session_id,
        "ttl_ms": 30000, "slot": "retrieved_evidence", "body": redacted,
        "budget": selection["ledger"],
        "policy": {"sensitivity_max": "low"},
        "provenance": [],
        "scope": scope,
    }
    response = {
        "patches": [patch],
        "ledger": selection["ledger"],
        "stage_a": {"executed": executed_ids, "ledger": plan["ledger"]},
        "trace": selection["trace"],
    }
    if FLAGS.is_enabled("dspy_logging"):
        DATA_LOGGER.log_propose(p, response["stage_a"], selection, patch)
    return response

@app.get("/review/candidates")
def review_candidates(session_id: str, limit: int = 20):
    items = PRIVATE.query_session(session_id, limit=limit)
    return {"session_id": session_id, "candidates": items}

@app.post("/review/export_patch")
def review_export(req: ManualExport):
    selected = []
    for cid in req.candidate_ids:
        item = PRIVATE.get(cid)
        if item:
            selected.append(item)
    texts = [item.get("content",{}).get("text","") for item in selected]
    fragments = {
        "task_header": (req.note or (selected[0].get("content",{}).get("text","") if selected else ""))[:200],
        "retrieved_evidence": "\n\n".join(texts)[:800],
        "citations": "\n".join(
            cite.get("cite")
            for item in selected
            for cite in item.get("provenance", [])
            if cite.get("cite")
        )[:200],
    }
    blueprint = compose(req.slot_specs, fragments)
    scope = {"tenant":"demo","project":"demo","user":req.session_id}
    patch = {
        "id": f"manual-{req.session_id}",
        "task_id": f"{req.session_id}-manual",
        "target_session_id": req.session_id,
        "ttl_ms": 60000,
        "slot": "retrieved_evidence",
        "body": blueprint,
        "policy": {"sensitivity_max": "low"},
        "provenance": [],
        "note": req.note,
        "scope": scope,
    }
    record = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "session_id": req.session_id,
        "selected": [item.get("id") for item in selected],
        "note": req.note,
        "patch_id": patch["id"],
    }
    AUDIT.append(record)
    return {"patch": patch, "selected": record["selected"]}

@app.get("/review/audit")
def review_audit(limit: int = 50):
    return {"audit_log": AUDIT.tail(limit)}

@app.get("/metrics/observer")
def observer_metrics():
    return METRICS.snapshot()

@app.get("/metrics/dspy")
def dspy_metrics():
    return summarize_propose_logs(DATA_LOGGER.path)

@app.post("/patches/inject")
def inject_patch(req: InjectPatch):
    scope = req.patch.get("scope") or {"tenant":"demo","project":"demo","user":req.patch.get("target_session_id","demo")}
    if not CONSENTS.has_consent(scope["tenant"], scope["project"], scope["user"]):
        raise HTTPException(status_code=403, detail="No consent on record for this scope")
    policy = POLICY.evaluate(req.patch, scope)
    if not policy["allowed"]:
        raise HTTPException(status_code=400, detail=policy["reason"] or "Policy violation")
    result = BROKER.inject(req.patch, req.transport)
    AUDIT.append(
        {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "session_id": req.patch.get("target_session_id"),
            "patch_id": req.patch.get("id"),
            "transport": result["transport"],
            "ack": result["ack"],
            "policy": policy,
        }
    )
    return {"ok": True, "transport": result["transport"], "ack": result["ack"]}

@app.post("/governance/consent")
def set_consent(req: ConsentRequest):
    CONSENTS.grant(req.tenant, req.project, req.user, req.consent)
    return {"ok": True}

@app.get("/feature_flags")
def get_feature_flags():
    return {"flags": FLAGS.all()}

@app.post("/feature_flags")
def set_feature_flag(name: str, value: bool):
    FLAGS.set(name, value)
    return {"ok": True, "flags": FLAGS.all()}

@app.post("/transports/chaos")
def set_transport_state(req: TransportChaosRequest):
    if not BROKER.set_availability(req.transport, req.available):
        raise HTTPException(status_code=404, detail="Unknown transport")
    return {"ok": True}

@app.get("/transports/status")
def transport_status():
    return BROKER.status()

@app.get("/skills")
def list_skills(session_id: str, cohort: str | None = None):
    scope = {"tenant":"demo","project":"demo","user":session_id}
    if not CONSENTS.has_consent(scope["tenant"], scope["project"], scope["user"]):
        raise HTTPException(status_code=403, detail="Consent required to view skills")
    SKILLS.sync(GRAPH.get_skills())
    return {"skills": SKILLS.list(cohort)}

@app.post("/skills/share")
def share_skill(req: ShareSkillRequest):
    SKILLS.sync(GRAPH.get_skills())
    if not SKILLS.share(req.skill_id, req.cohort):
        raise HTTPException(status_code=404, detail="Unknown skill")
    AUDIT.append(
        {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "skill_id": req.skill_id,
            "action": "share",
            "cohort": req.cohort,
        }
    )
    return {"ok": True}
