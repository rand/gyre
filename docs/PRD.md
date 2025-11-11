# PRD — Gyre vNext: Autonomous Memory & Context Orchestrator

Date: 2025-02-15  
Owner: Systems & Agentic Platforms  
Status: Vision-Aligned Draft (supersedes `archive/PRD_2025-11-11.md`)

## Executive Summary
Gyre vNext is a proactive context supervisor that continuously **observes**, **plans**, and **injects** high-signal patches into multi-agent sessions. It unifies lifelong memory, live tool use, and cohort knowledge under one selection objective, maximizing *efficacy per injected token* while honoring strict safety and latency envelopes.

## Problem Statement
Modern agent fleets (Claude Code, Codex, Gemini, in-house copilots) operate in isolation from their accumulated knowledge. Context loss drives redundant tool calls, hallucinated instructions, and human escalation. Current memory add-ons hoard logs or simple vector hits, ignoring provenance, cost, scope, or usefulness, resulting in:
- Token & latency waste from indiscriminate recall.
- Policy violations due to ad-hoc redaction.
- Manual babysitting to paste reminders and guardrails.

## Vision
Deliver a *drop-in memory cortex* that passively taps session streams, curates policy-safe candidates across working/episodic/semantic/procedural/meta layers, plans deferred queries only when expected value justifies their cost, and composes slot-based Context Patch Protocol (CPP) payloads tailored to each host agent. Gyre behaves like a co-pilot’s chief of staff: unseen yet always ready with the right, auditable context at the right moment.

## Design Principles
1. **Utility-per-token > Recall volume** — every token must pay rent through measured outcome lift.  
2. **Uniform candidate substrate** — memory items, live tool results, skills, and “query plans” share the same schema and scoring path.  
3. **Budgets everywhere** — tokens, latency, risk, dollars, attention all treated as first-class ledgers.  
4. **Citations before confidence** — nothing ships without provenance and scope checks.  
5. **Graceful degradation** — observe-only, private-store-only, and manual inject modes must keep SLOs even when DSPy/graph/transport layers fail.  
6. **Learning loop** — credit assignment feeds DSPy optimizers so selection, summarization, redaction, and EV estimators improve from real logs.  
7. **Transparency** — every patch is explainable, replayable, and reviewable.

## Target Users & Jobs
| Persona | Jobs-to-be-done |
| --- | --- |
| Agent platform engineers | Plug memory supervisor into Realtime/chat transports without rewriting agents. |
| Ops/SRE/Compliance | Audit provenance, scope, and safety budgets; enforce per-tenant policies. |
| Prompt engineers / applied researchers | Iterate on retrieval/selection/summary behaviors with real-time metrics and DSPy compiles. |
| Downstream agents (indirect) | Receive succinct patches that unlock blocked tasks or avoid repetition. |

## Core Use Cases
1. **Silent Observe** — tap IDE/tool/chat streams, normalize into task state, and log high-signal deltas without requiring agent cooperation.  
2. **Proactive Inject** — when task risk/latency budgets allow, push CPP patches into live sessions via OpenAI/Anthropic/Gemini transports.  
3. **On-demand Assist** — respond to explicit “need context” calls with tailored slot blueprints.  
4. **Cohort Memory & Skills** — promote vetted learnings to shared skill catalogs with consent + scope.  
5. **Audit & Replay** — replay observe→select→inject decisions with budget ledgers and redaction diffs.

## Functional Requirements
1. **Observe & Encode**  
   - Session tap SDKs & proxy connectors for chat, tools, IDE events.  
   - Canonical observer emits Context Candidates with provenance, scopes, graph anchors, novelty signals.  
2. **Unified Stores**  
   - Private per-session store (KV + vector) for hot items.  
   - Temporal knowledge graph for shared facts, skills, and cohort memories with bitemporal validity.  
   - Object store for raw payloads / attachments.  
3. **Retrieval & Planning**  
   - Hybrid lexical/vector/graph retriever conditioned on task intent and entity neighborhood.  
   - Deferred query planner that scores EV vs. latency/tokens before execution.  
4. **Budgeted Selection**  
   - Two-stage knapsack + MMR selector with explicit ledgers for tokens, latency, dollars, risk, freshness.  
   - Cooling periods per scope; redundancy and staleness penalties; slot-aware diversity.  
5. **Composition & CPP**  
   - Slot blueprints (task header, constraints, prefs, retrieved evidence, tool args, citations, extensions).  
   - Compression ops (dedupe, distill, cite, redact) executed under slot caps.  
   - Patch serialization with TTLs, policies, and provenance.  
6. **Transports & Injection**  
   - Providers: OpenAI Realtime/system patches, Anthropic Computer Use actions, Gemini function calls.  
   - Transport broker chooses best route, handles retries, and logs acknowledgements.  
7. **Governance & Safety**  
   - Policy packs per tenant (allowed scopes, sensitivity, consent registry).  
   - Redaction, PII scrubbing, and risk scoring before injection.  
   - Immutable audit log (patch, ledger, policy verdict, outcome).  
8. **Learning & Evaluation**  
   - DSPy signatures (ObserveSession, ProposePatches, RankCandidates, SummarizeForSlot, EVofDeferredQuery, RedactForScope, BlueprintFill).  
   - Dataset seeding, labeling workflows, and automated MIPROv2/COPRO compiles.  
   - Offline + online evaluation harness (efficacy-per-1k tokens, redundancy, staleness, latency, safety).  
9. **Reliability & Ops**  
   - Decoupled observe/inject queues with backpressure and circuit breakers.  
   - Health SLOs: observe→inject p95 ≤ 600 ms, p99 ≤ 1200 ms; error budget <0.1%.  
   - Observability via OpenTelemetry, structured logging, and replay tools.

## Non-Goals
- Replace host agent core reasoning loop.  
- Offer generic data-lake search or analytics beyond memory graph needs.  
- Introduce opaque black-box decisions; every selection step must be explainable.  
- Manage credential storage for host agents; we consume scoped tokens only.

## Success Metrics
**Leading indicators**:  
- Retrieval precision@k ≥ 0.75 on benchmark tasks.  
- Redundancy ratio < 0.15 of injected tokens.  
- Staleness rate < 5% of facts past freshness half-life.  
- Coverage of provenance ≥ 99.5% of emitted tokens.  

**Lagging indicators**:  
- Δ task success / 1k injected tokens ≥ +12% vs. baseline.  
- Patch acceptance rate ≥ 70% in silent trials.  
- 0 policy violations per 10k injections in staging.  
- Observe→inject p95 ≤ 600 ms; transport failure auto-recovery ≤ 30 s.

## Release Plan
| Milestone | Scope | Exit Criteria |
| --- | --- | --- |
| **M0: Traceable Observe** | Session tap SDK, observer v2, private store with novelty filters, manual CPP export. | ≥2 provider streams ingested; observer emits schema-complete candidates with provenance; audit dashboard for manual reviewers. |
| **M1: Budget-aware Selection** | Deferred query planner, EV gate, knapsack+MMR selector, slot composer, manual transport push. | Demonstrated efficacy lift on 3 replay tasks; budget ledger + redundancy metrics logged per patch. |
| **M2: Proactive CPP Injection** | Transport broker for OpenAI, governance service (policy packs + redactor), automated CPP injection. | Closed-loop observe→inject under 600 ms p95 in canary; zero leakage findings during red-team suite. |
| **M3: Temporal Graph & Skills** | Bitemporal graph store, consolidation jobs, skill promotion workflow, consented cohort sharing. | Graph queries power ≥30% of selected context; skill promotions tracked with win-rate >55%. |
| **M4: Adaptive Learning Loop** | DSPy compiles with >1k labeled traces, online evaluation harness, self-tuning thresholds. | Rank/Summarize/Redact programs show ≥10% improvement over hand-tuned baselines; automated retraining pipeline deployed. |

## Risks & Mitigations
| Risk | Impact | Mitigation |
| --- | --- | --- |
| Over-injection harms host agent reasoning | Task regressions, cost spikes | Strict budgeter, cooldowns, delta patches, host feedback hooks. |
| Privacy leakage / scope violations | Compliance breach | Pre-compose redaction, consent registry, immutable audits, scoped credentials. |
| Latency spikes from heavy retrieval | Missed SLAs | EV gate live queries, cache hot fragments, degrade to private-store-only. |
| Graph/store bloat | Cost + recall noise | TTL + consolidation policies, nightly pruning, per-tenant quotas. |
| DSPy model drift | Wrong selection / summaries | Offline eval harness, canary tests, rollbacks with deterministic heuristics. |

## Dependencies & Open Questions
- Provider contracts and rate limits for long-lived Realtime sessions.  
- Choice of graph backend (Neo4j vs. pgvector + NetworkX) for production scale.  
- Consent UX for cohort skill sharing.  
- Budget ledger UX for SRE/compliance review.  
- Labeling workforce or synthetic generation for DSPy training corpora.

## References
- `archive/PRD_2025-11-11.md` — prior vision (deprecated).  
- “Agentic memory definition” session notes (`Agentic memory definition.html`).  
- DSPy papers, GraphRAG literature, Generative Agents (see `RESEARCH-REFERENCES.md`).

## Change Log
- 2025-02-15 — vNext PRD authored; prior assets archived. 
