# SPEC — Gyre vNext Interfaces & Architecture

Date: 2025-02-15  
Status: Drafted alongside `PRD.md`; supersedes `archive/SPEC_2025-11-11.md`.

## 0. Scope & Assumptions
- System provides passive observation, candidate curation, budgeted selection, CPP composition, and provider-specific injection for multi-agent environments.
- Host agents remain unchanged; Gyre interacts through taps/transports with explicit scopes and credentials.
- DSPy layer is optional but recommended; deterministic heuristics must exist for degraded operation.

## 1. System Context
```
Session Tap SDKs → Observer → Candidate Bus → {Private Store, Temporal Graph}
                                         ↘ Deferred Query Planner ↘ Tool Runtimes
Candidates + Plans → Selector → Composer → Redactor/Governance → CPP Patches
CPP Patches → Transport Broker → Provider APIs (OpenAI, Anthropic, Gemini)
All stages → Metrics/Audit/Replay Store → DSPy Training Pipelines
```

## 2. External APIs
### POST /sessions/register
Registers a live session with metadata and scopes.
```json
{
  "session_id": "uuid",
  "agent_kind": "openai|anthropic|gemini|other",
  "capabilities": ["system_patch","tool_result","realtime","computer_use"],
  "scopes": {"tenant":"acme","project":"gyro","user":"dev-42"},
  "preferences": {"max_patch_tokens": 800, "allow_proactive": true}
}
```
Returns `{ "ok": true, "session_token": "..." }`.

### POST /observe/ingest
Streams batched events from taps.
```json
{
  "session_id": "...",
  "events": [
    {"t":"2025-02-15T00:00:00Z","kind":"user","payload":{"text":"...","channel":"chat"}},
    {"t":"...","kind":"tool","payload":{"name":"jira.search","args":{...},"result":null}}
  ]
}
```
Response includes derived task descriptor, novelty signals, and candidate ids written.

### POST /patches/propose
Requests proactive assistance under explicit budgets.
```json
{
  "session_id": "...",
  "task_desc": "...",
  "budgets": {
    "tokens": 1200,
    "latency_ms": 800,
    "risk": "low",
    "dollars": 0.08
  },
  "slot_specs": [
    {"name":"task_header","max_tokens":200},
    {"name":"constraints","max_tokens":250},
    {"name":"user_prefs","max_tokens":120},
    {"name":"retrieved_evidence","max_tokens":600},
    {"name":"citations","max_tokens":120}
  ],
  "mode": "proactive|respond"
}
```
Returns candidate IDs, selection reasons, CPP patches, and budget ledger.

### POST /patches/inject
```json
{ "session_id":"...", "patch_id":"...", "transport":"best|openai|anthropic|gemini" }
```
Response contains ACK id, routed transport, policy verdict, and latency metrics.

### GET /patches/audit
Filters by session/tenant/time; returns provenance, redaction diff, ledger, and outcome notes.

### GET /metrics/transports
Returns per-transport SLA metrics:
```json
{
  "transports": {
    "openai": {"success": 12, "failure": 1, "avg_latency_ms": 210.4, "last_latency_ms": 198.2, "last_error": null},
    "anthropic": {"success": 10, "failure": 2, "avg_latency_ms": 280.0, "last_latency_ms": 310.5, "last_error": "503: overload"}
  }
}
```

### GET /metrics/prometheus
Exposes Prometheus-formatted metrics (ingest counts, selection tokens, transport success/failure, latency histograms) for scraping.

### POST /patches/feedback
Hosts report accept/reject decisions.
```json
{
  "patch_id": "patch-1",
  "session_id": "sess-123",
  "verdict": "accepted",
  "reason": "used in next turn",
  "transport": "openai"
}
```
Response includes appended record and aggregate stats.

### GET /patches/feedback
Returns feedback stats and recent entries for reviewer dashboards.

### GET /pilot/status
Indicates whether pilot gating is active (based on `config/pilot_cohorts.json`).

## 3. Data Contracts
### Context Candidate
```json
{
  "id": "src:memory:m_4821",
  "kind": "working|episodic|semantic|procedural|meta|file_chunk|tool_result|skill|deferred_query",
  "content": {
    "text": "...",
    "struct": {...},
    "attachments": ["obj://..."]
  },
  "source": "tap:vim|tool:jira.search|graph:skill:123",
  "timestamp": "2025-02-15T00:00:00Z",
  "features": {
    "relevance": 0.74,
    "actionability": 0.62,
    "freshness": 0.88,
    "reliability": 0.91,
    "importance": 0.4,
    "ev_per_ms": 0.003,
    "novelty": 0.57
  },
  "costs": {"tokens_est": 110, "latency_est_ms": 25, "dollars_est": 0.0004},
  "risks": {"sensitivity":"medium","scope":"tenant|project|user","leakage":0.02},
  "provenance": [{"cite":"doc://jira/123","hash":"sha256:...","confidence":0.94}],
  "graph": {"entities":["PartCatalog","DenverEmissions"],"relations":[{"to":"PartsShopA","rel":"quoted"}],"valid":["2024-12-01","2025-06-01"]},
  "status": "raw|summarized|refined|skill",
  "credit": {"wins":12,"losses":3,"last_seen":"..."}
}
```

### Budget Ledger
```json
{
  "tokens_used": 620,
  "tokens_cap": 800,
  "latency_ms_used": 410,
  "latency_ms_cap": 800,
  "dollars_used": 0.045,
  "dollars_cap": 0.08,
  "risk_consumed": "low",
  "risk_cap": "medium",
  "cooldowns": {"tenant:acme": "5s", "session:xyz": "0s"}
}
```

### CPP Patch
Extends prior spec with slot metadata and compression audit.
```json
{
  "id": "patch-2025-02-15T12:00:00Z-001",
  "task_id": "session:xyz:turn:32",
  "target_session_id": "xyz",
  "ttl_ms": 45000,
  "blueprint": {
    "slots": [
      {"name":"task_header","content":"...", "tokens":120},
      {"name":"constraints","content":"...", "tokens":180, "citations":["doc://..."]},
      {"name":"retrieved_evidence","content":"...", "tokens":260}
    ]
  },
  "policy": {"allowed_scopes":["tenant:acme","project:gyro"],"sensitivity_max":"medium"},
  "provenance": [...],
  "ledger": {...},
  "redaction_diff": {"removed":["PII.email"], "justification":"scope:user mismatch"}
}
```

## 4. Component Specifications
### 4.1 Observer Service
- Ingests event batches, infers task descriptors (LLM-backed + heuristics), extracts entities, and emits candidate drafts to the candidate bus.  
- Dedupes via semantic similarity and key fields; enforces write policies (novelty threshold, TTL).  
- Persists to PrivateStore (Redis/pg) and pushes graph updates (Neo4j/NetworkX).

### 4.2 Stores
- **PrivateStore**: per-session KV+vector (pgvector/FAISS) with TTL, rate limits, and scope filters.  
- **TemporalGraph**: multi-tenant, bitemporal facts; adjacency limited to N hops per query; nightly consolidation jobs to merge, decay, and promote skills.  
- **ObjectStore**: S3-compatible bucket storing attachments referenced via signed URLs.

### 4.3 Retrieval Layer
- Intent-conditioned lexical/vector/graph searches run in parallel with budgets.  
- Re-ranker (cross-encoder) scores top-K hits; candidate features updated accordingly.  
- Graph neighborhood retrieval limited by latency quota; caches canonical subgraphs for repeated intents.

### 4.4 Deferred Query Planner
- Generates `kind="deferred_query"` candidates with EV estimate (reward delta × success probability) and cost (token + latency).  
- Stage A selection chooses subset maximizing EV-per-cost under planner budget; executed queries write results back as standard candidates with provenance linking to the plan.

### 4.5 Selector
- Implements two-stage greedy algorithm:
  1. `SelectQueries`: maximize Σ(EV_i) subject to Σ cost_i ≤ planner budget, with gating on risk and cooldowns.  
  2. `SelectContext`: submodular utility `u_i = w·features - λ·redundancy - μ·staleness - ν·risk`, solved via knapsack+MMR using ledgers, optionally pre-ordered by the DSPy `RankCandidates` program (flag `dspy_selection`).  
- Outputs explanation trace (marginal gain, budget usage, rejection reason).

### 4.6 Composer & Compression
- `BlueprintFill` signature arranges fragments per slot specs; deterministic fallback merges top candidates per slot, truncating by token caps.  
- Compression operators include: `dedupe_by_source`, `merge_citations`, `summarize_with_guardrails`, `cite_or_drop`.  
- Each slot retains link to source candidate IDs and tokens consumed for audit.

### 4.7 Governance & Redaction
- Policy engine resolves effective scope and sensitivity thresholds from tenant/project/user + consent registry.  
- `RedactForScope` signature plus deterministic regex/PII scrubber produce redaction diff.  
- Risk budgeter tracks leakage probability, sensitivity mix, and denies injection if caps exceeded.  
- Immutable audit log stored in Postgres/Parquet with schema `[patch_id, session_id, ledger, policy, provenance, outcome, reviewer_notes]`.

### 4.8 Transport Broker
- Chooses provider channel based on session capabilities, budget headroom, and transport health.  
- OpenAI: Realtime/system patch; Anthropic: Computer Use tool/action; Gemini: function call.  
- Handles retries with idempotency tokens, circuit breakers, ack telemetry, and publishes `/metrics/transports` for SLA dashboards.
- Credentials load from `.env` (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`) or `config/transports.json` (per-tenant/project overrides with `rate_limit_per_min`). When `GYRE_TRANSPORT_FORCE_STUB=1` or keys are absent, adapters fall back to local stub acks to keep tests offline.

### 4.9 DSPy Programs
| Signature | Purpose | Metric / Optimizer |
| --- | --- | --- |
| ObserveSession | Task state inference from events | Accuracy vs. labeled states — COPRO |
| ProposePatches | Draft slot fragments | Faithfulness + budget compliance — MIPROv2 |
| RankCandidates | Stage-B ordering | NDCG@k with redundancy penalties — MIPROv2 |
| SummarizeForSlot | Slot compression with citations | Rouge-L + citation overlap — MIPROv2 |
| EVofDeferredQuery | EV estimates | Correlation with realized reward — COPRO |
| RedactForScope | Policy-compliant redaction | Zero violations — COPRO |
| BlueprintFill | Slot arrangement | Downstream success + cap compliance — MIPROv2 |

All DSPy datasets are produced from the `/patches/propose` logger via `scripts/build_dspy_datasets.py`, which emits `rank|sum|ev|red|blue_{train,eval}.jsonl` along with coverage metrics (positive rate, execution rate, slot counts). Compilation scripts (`scripts/compile_dspy.py`, `scripts/evaluate_dspy.py`) consume these files directly.

Fallback deterministic heuristics mirror existing stubs (`gyre/observer.py`, `gyre/selector.py`, etc.) for offline/dev usage.

## 5. Performance & Capacity
- Observe→inject critical path ≤ 600 ms p95 (excluding provider ack).  
- Candidate write throughput: ≥ 1k events/s per node with backpressure to taps.  
- Graph queries limited to ≤ 50 ms budget; caches refreshed every 5 min.  
- Transport retries exponential backoff capped at 2s; degrade to manual inject after 3 failures.  
- Resource targets: memory footprint per session ≤ 40 MB hot set, graph growth ≤ 5 GB/week per tenant (pre-pruning).

## 6. Reliability & Operations
- Separate workloads: `observer`, `planner`, `selector`, `composer`, `transport`, `governance` microservices communicating via NATS/Redis streams.  
- Circuit breakers per transport; degrade to observe-only when budgets exhausted or policy blocks injection.  
- Health probes: ready/live endpoints, synthetic transactions, red-team scripts.  
- Observability: OpenTelemetry tracing, metrics (Prometheus), structured logs, replay CLI for audits.  
- Disaster recovery: hourly snapshots of private store + graph diffs, object store versioning.

## 7. Security & Compliance
- Tenant isolation via scoped API tokens and per-tenant encryption keys.  
- Consent registry ensures cohort skill sharing only across approved projects.  
- PII detection using deterministic regex + ML classifier; redact logs store hashed originals for forensics.  
- All provider credentials referenced via env/secret manager; Gyre never stores host agent secrets beyond session tokens.

## 8. Testing & Evaluation
- **Unit**: deterministic tests for observer parsers, selector math, governance policies (expand `tests/`).  
- **Contract**: schema validation for APIs using Pydantic models.  
- **Replay/Simulation**: deterministic scenarios covering EV planning, budget exhaustion, and transport failure.  
- **Chaos/Load**: stress observe/inject queues, fail transports, throttle vector/graph stores.  
- **Evaluation Harness**: offline replayer computing efficacy/token, redundancy, staleness, leakage metrics; integrates with DSPy compile pipeline.

## 9. Tooling & Developer Experience
- `uv`-based workflows: `make setup|run|test|lint|seed`.  
- Scenario simulator to stream recorded sessions and inspect selection traces.  
- Labeling toolkit for DSPy datasets (front-end or CLI).  
- Documentation updates: `docs/AGENTS.md` (contributor guide), new PRD/SPEC references.

## 10. Migration Notes
- Legacy docs retained in `archive/`.  
- Existing code stubs (observer, retriever, selector, composer, governance) remain entry points but must evolve toward specs above.  
- All new work must reference PRD/SPEC versions in headers and note deviations for review.

## Appendices
- A. Research bibliography: see `RESEARCH-REFERENCES.md`.  
- B. Minimal worked example: replicate “coil-spring conversion” scenario to validate end-to-end flow.  
- C. Glossary: CPP, EV, DSPy, Candidate, Slot, Ledger, Scope, Consent Registry.
