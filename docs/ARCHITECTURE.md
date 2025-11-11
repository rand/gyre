# ARCHITECTURE — Gyre vNext Alignment

> **Precedence:** `PRD.md` (vision/why) → `SPEC.md` (contracts) → `ARCHITECTURE.md` (how). If this document diverges from the PRD or SPEC, treat those as canonical and open a beads issue to reconcile.

## 1. Component Map

| Layer | Responsibilities | Key Artifacts |
| --- | --- | --- |
| **Session Tap SDKs / Proxies** | Mirror chat/tool/IDE streams without mutating host agents. | `gyre.taps` helpers, OpenAI Realtime + Anthropic adapters, `scripts/pipe_provider_events.py`, replay script. |
| **Observer Service** | Normalize events, infer task state, detect novelty, emit context candidates. | `ObserveSession` DSPy program, heuristics fallback, schema validation. |
| **Candidate Bus & Stores** | Fan-out canonical candidates to: (a) PrivateStore (per-session KV+vector) and (b) TemporalGraph (multi-tenant bitemporal graph) with object-store payload references. | Redis/NATS stream, Postgres/pgvector, NetworkX/Neo4j, S3-compatible bucket. |
| **Retrieval Layer** | Hybrid lexical/vector/graph search plus cross-encoder re-ranking scoped by task intent + entities. | `retriever.py`, pgvector indices, graph neighborhood caching. |
| **Deferred Query Planner** | Generates and scores `deferred_query` candidates (expected value vs. token/latency cost) and executes the subset selected in Stage A. | `gyre/planner.py`, `EVofDeferredQuery` DSPy program, tool runtimes, planner budget ledger. |
| **Selector** | Two-stage greedy knapsack + MMR respecting token/latency/risk/dollar ledgers, redundancy penalties, cooldowns. | `selector.py` (ledger+trace), future DSPy ranker, dependency tracing. |
| **Composer & Compression** | Convert chosen candidates into slot-based blueprints (task header, constraints, prefs, evidence, tool args, citations) while enforcing slot caps and dedupe/citation guarantees. | `composer.py` (token-aware slots), `BlueprintFill` + `SummarizeForSlot`, compression operators. |
| **Governance & Redaction** | Apply policy packs (scope, sensitivity, consent), redact sensitive payloads, log provenance + redaction diffs, block injection if budgets exceeded. | `governance.py`, consent registry (`gyre/consent.py`), audit store (`gyre/audit.py`). |
| **Reviewer Console** | Surface recent candidates, ledgers, manual exports, and audit history. | `/review/candidates`, `/review/export_patch`, `/review/audit`, `scripts/reviewer_cli.py`, future UI. |
| **Transport Broker** | Route Context Patch Protocol (CPP) payloads to OpenAI Realtime, Anthropic Computer Use, Gemini function calling, with retries/circuit breakers and chaos hooks. | `gyre/transports/broker.py`, transport adapters, ack telemetry, `/transports/chaos`. |
| **Learning & Evaluation** | Collect labels, compile DSPy programs (MIPROv2/COPRO), replay sessions to measure efficacy-per-token, redundancy, staleness, safety. | `scripts/seed_datasets.py`, `scripts/evaluate_selection.py`, evaluation harness, OpenTelemetry traces, `/metrics/observer`. |

## 2. Control & Data Flow
1. **Observe** — Taps push batches to `/observe/ingest`. The observer infers task descriptors, extracts entities, and emits normalized candidates onto the bus with scopes/provenance. Writes land in both PrivateStore (hot working set) and TemporalGraph (shared memory) with object-store blobs for attachments.
2. **Plan Queries** — When `/patches/propose` arrives (proactive or explicit), the planner inspects current budgets. Stage A selects high-EV deferred queries to execute under strict latency/tokens caps; results are written back as fresh candidates linked to their originating plan.
3. **Select Context** — Retrieval pulls relevant candidates (memory, file chunks, tools, skills, cohort notes) and refreshes their feature vectors. Stage B of the selector performs submodular greedy selection with MMR diversity, updating the budget ledger after each choice and leaving an explanation trace (marginal gain, rejection reasons).
4. **Compose Blueprint** — The composer groups selected candidates by slot, runs compression (dedupe, summarize with citations, distill tool args), and produces a typed CPP blueprint.
5. **Govern & Redact** — Governance engine loads applicable policy pack (tenant/project/user consent), redacts sensitive fields, and computes risk consumption. If caps are exceeded, the patch is rejected with audit evidence.
6. **Inject & Audit** — Transport broker chooses the healthiest route given session capabilities and budget headroom, injects the CPP payload, and records ack latency. Every patch plus ledger, redaction diff, and outcome enters the immutable audit log and feeds the evaluation/learning loop.

## 3. Deployment & Topology
- **Services**: `observer`, `planner`, `selector`, `composer`, `governance`, `transport`, and `metrics` services communicate via Redis/NATS streams. Horizontal scaling is driven by stream partitioning.
- **Storage**: Postgres (metadata + audit), pgvector (private store), Redis (hot cache), Neo4j/NetworkX (graph prototypes), S3-compatible object store (attachments). Hourly snapshots defend against corruption.
- **DSPy**: Modules run in-process with deterministic fallbacks. Compiles happen offline using logged datasets; artifacts are versioned and can roll back instantly.

## 4. Reliability, Performance, and Safety Hooks
- Observe→inject p95 must stay ≤ 600 ms (excluding provider ack). Budget ledgers live in Redis for constant-time checks.
- Backpressure: each stream has bounded queues; when downstream lags, taps are throttled and the system falls back to observe-only mode.
- Circuit breakers per transport + provider-specific cooldown windows. After three failed injections, requests downgrade to manual approval.
- Governance always runs before injection; provenance hashes and policy verdicts are stored immutably (Postgres table + Parquet export).
- Monitoring: OpenTelemetry traces every stage, Prometheus metrics include latency histograms, redundancy/staleness ratios, and risk ledger utilization. Replay CLI can reconstruct any patch end-to-end for audits.

## 5. Open Questions & Future Work
- Neo4j vs. light-weight NetworkX for temporal graph once data volume grows.
- Cohort skill promotion UX + consent registry integration (ties into SPEC §10).
- Automated evaluation harness packaging for partners (aligns with PRD success metrics).

Keep this document updated whenever implementation decisions change service boundaries, data contracts, or operational posture. All substantive changes should reference a beads issue ID for traceability.
