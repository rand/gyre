# Gyre :: Agentic Memory Supervisor

Gyre is a proactive memory supervisor for AI agents. It **observes** every turn of an agent session, plans high-value retrievals, and **injects** minimal Context Patch Protocol (CPP) payloads through provider transports (OpenAI Realtime, Anthropic Computer Use, Gemini function calls). The service keeps safety, provenance, and token budgets front‑and‑center so copilots stay on task without hallucinated context or policy violations.

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Quickstart](#quickstart)
3. [Project Layout](#project-layout)
4. [Key Workflows](#key-workflows)
5. [HTTP & CLI Surface](#http--cli-surface)
6. [Development Workflow](#development-workflow)
7. [Testing & Evaluation](#testing--evaluation)
8. [Roadmap & References](#roadmap--references)

---

## Architecture Overview

| Layer | Responsibilities | Key Modules |
| --- | --- | --- |
| **Session Taps** | Mirror chat/tool/IDE streams without modifying host agents. | `gyre.taps.*`, `scripts/replay_session.py`, `scripts/pipe_provider_events.py` |
| **Observer** | Canonicalize events, infer task state, compute novelty signals. | `gyre/observer.py`, `/observe/ingest` |
| **Stores & Planner** | Persist private working sets, update the temporal graph, run Stage‑A deferred query planner. | `gyre/stores/*`, `gyre/planner.py` |
| **Selector & Composer** | Stage‑B knapsack+MMR selection under budgets, slot-based composition with citations. | `gyre/selector.py`, `gyre/composer.py` |
| **Governance & Audit** | Consent registry, policy packs, redaction, immutable audit log. | `gyre/governance.py`, `gyre/consent.py`, `gyre/audit.py` |
| **Transports** | Broker CPP payloads into provider transports with health/chaos controls. | `gyre/transports/broker.py`, `/patches/inject`, `/transports/status` |
| **Evaluation & Tooling** | Replay traces, generate datasets, reviewer console. | `scripts/evaluate_selection.py`, `scripts/reviewer_cli.py`, `tests/*` |

Gyre’s product intent, spec, and architecture live in `docs/PRD.md`, `docs/SPEC.md`, and `docs/ARCHITECTURE.md`. Those documents set the precedent order; match code to the PRD first.

---

## Quickstart

```bash
# Bootstrap environment (requires Python ≥ 3.10)
uv venv
uv pip install -e .

# Configure secrets
cp .env.example .env
# export OPENAI_API_KEY=..., ANTHROPIC_API_KEY=..., GEMINI_API_KEY=...

# Seed toy datasets
uv run python scripts/seed_datasets.py

# Run the dev server (FastAPI + stub transports)
uv run python server/run_dev_server.py
```

Smoke test the pipeline end-to-end:
```bash
# Ingest a recorded trace
uv run python scripts/replay_session.py --session demo --trace traces/example.jsonl

# Request a patch
curl -X POST http://localhost:8000/patches/propose \
  -H 'Content-Type: application/json' \
  -d @scripts/examples/propose.json

# Grant consent and inject the patch through the OpenAI transport stub
curl -X POST http://localhost:8000/governance/consent \
  -d '{"tenant":"demo","project":"demo","user":"demo","consent":true}' \
  -H 'Content-Type: application/json'

curl -X POST http://localhost:8000/patches/inject \
  -H 'Content-Type: application/json' \
  -d '{"patch":{...from propose...},"transport":"openai"}'
```

---

## Project Layout

```
├── docs/PRD.md / docs/SPEC.md / docs/ARCHITECTURE.md / AGENTS.md
├── gyre/
│   ├── observer.py / planner.py / selector.py / composer.py
│   ├── stores/               # Private store + temporal graph prototype
│   ├── transports/           # Provider adapters + broker
│   ├── taps/                 # OpenAI/Anthropic adapters + replay helpers
│   ├── governance.py         # Policy engine + redaction
│   ├── consent.py / audit.py
│   └── telemetry.py
├── server/run_dev_server.py  # FastAPI surface for ingest/propose/inject/review
├── scripts/                  # Replay, provider piping, reviewer CLI, eval harness
├── tests/                    # Pytest coverage for every layer
└── data/                     # `audit.log`, `consent.json`, eval traces (gitignored except placeholders)
```

---

## Key Workflows

### Observe → Plan → Select → Compose
1. `/observe/ingest` normalizes tap events and writes candidates/graph entities.
2. Stage‑A planner (`gyre/planner.py`) emits `deferred_query` candidates and executes the highest EV queries under latency/token budgets.
3. Stage‑B selector (`gyre/selector.py`) runs knapsack + MMR, returning `selected`, `ledger`, and `trace` so every token and millisecond is accounted for.
4. Composer (`gyre/composer.py`) fills slot blueprints with per-slot token counts; both proactive and manual reviewers use the same blueprint.

### Governance & Transports
1. Register per-scope consent via `POST /governance/consent`.
2. `/patches/inject` validates consent, enforces policy packs, and forwards patches through the broker. Responses include transport acks; failures trigger cooldowns viewable via `GET /transports/status`.
3. `data/audit.log` stores every manual/proactive patch action; reviewers can tail it via `GET /review/audit` or the CLI.

### Evaluation
Use `scripts/evaluate_selection.py --trace traces/example.json --budget-tokens 600 --budget-latency 600` to replay recorded candidates through Stage A/B, reporting ledger stats and selection traces before shipping selector/planner changes.

---

## HTTP & CLI Surface

| Endpoint | Description |
| --- | --- |
| `POST /observe/ingest` | Ingest tap batches, output task state + novelty report. |
| `POST /patches/propose` | Run Stage A/B under explicit budgets; returns patch, Stage‑A ledger, Stage‑B ledger, and trace. |
| `POST /patches/inject` | Inject a patch through the broker (requires prior consent). |
| `GET /review/candidates` / `POST /review/export_patch` / `GET /review/audit` | Reviewer workflow for manual CPP exports and audits. |
| `POST /governance/consent` | Record tenant/project/user consent. |
| `POST /transports/chaos` / `GET /transports/status` | Toggle transport availability and view health/cooldown metrics. |
| `GET /metrics/observer` / `GET /metrics/dspy` | Observe→ingest telemetry plus Stage A/B token averages. |
| `GET /feature_flags` / `POST /feature_flags` | Inspect or toggle runtime flags (e.g., DSPy logging). |
| `GET /skills` / `POST /skills/share` | List promoted skills (consent-gated) and share them with cohorts. |

CLI helpers:
- `scripts/replay_session.py` — stream JSON/JSONL traces into `/observe/ingest`.
- `scripts/pipe_provider_events.py` — turn provider logs into ingest batches (`--provider openai|anthropic`).
- `scripts/reviewer_cli.py list|export` — inspect candidates and craft manual patches from the terminal.
- `scripts/evaluate_selection.py` — offline Stage A/B evaluation harness.
- `scripts/consolidate_graph.py` — prune stale nodes from the temporal graph (`--ttl-hours` defaults to 24) to keep persistence lean.
- `scripts/promote_skills.py` — promote high-signal nodes into the skill registry and sync them for sharing.
- `scripts/compile_dspy.py` / `scripts/evaluate_dspy.py` — compile DSPy programs from logged datasets and summarize Stage A/B performance; CI runs these in mock mode on every push.

---

## Development Workflow

1. **Docs First**: docs/PRD → docs/SPEC → docs/ARCHITECTURE → README/AGENTS. Align changes with the documents (open a beads issue if they diverge).
2. **Environment**: use `uv` for installs/tests (`uv run pytest -q`). Secrets live in `.env`.
3. **Issue Tracking**: run `bd quickstart` for the Beads workflow. Create tasks (`bd create "feat"`), model dependencies (`bd dep add`), and keep statuses updated (`bd update issue --status in_progress`).  
4. **Coding Guidelines**: Python ≥3.10, type hints, four-space indent. Prefer composition over inheritance; update or create `tests/test_<module>.py` alongside code changes.
5. **Policies & Consent**: before testing injections, grant consent via `POST /governance/consent`. The policy engine rejects over-budget patches.

---

## Testing & Evaluation

- Unit/integration suite: `uv run python -m pytest -q`. Tests cover taps, observer, planner, selector, transports, reviewer flows, governance, and evaluation harness.
- E2E smoke: run the dev server, replay a trace, request a patch, grant consent, and inject through a transport.
- Offline selection analysis: `scripts/evaluate_selection.py` surfaces Stage A/B ledger stats for any recorded trace.
- Chaos: `POST /transports/chaos` lets you simulate transport outages to ensure fallbacks + cooldowns behave.

---

## Roadmap & References

- **M2**: Proactive CPP injection with transport broker, policy/redaction, consent, and chaos testing (all staged here).  
- **M3**: Temporal graph hardening, skill promotion, and cohort sharing (see `ARCHITECTURE.md`).  
- **M4**: Adaptive DSPy learning loops and automated evaluation harnesses.

Research references: `RESEARCH-REFERENCES.md` aggregates the papers (ACE, DSPy, GraphRAG, etc.) that informed this design.

---

Gyre is built to be extended: replace the stub transports with real ones, wire your observability stack into the telemetry endpoints, and iterate on the planner/selector using the evaluation harness. Contributions that keep efficacy-per-token high and policies airtight are welcome.
