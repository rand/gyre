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
| **Transports** | Broker CPP payloads into provider transports with health/chaos controls. | `gyre/transports/broker.py`, `config/transports.json`, `/patches/inject`, `/transports/status`, `/metrics/transports` |
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
# (set GYRE_TRANSPORT_FORCE_STUB=1 while hacking locally to avoid real injections)

# Configure per-tenant transports (copy sample → real config)
cp config/transports.example.json config/transports.json
# fill tenant/project keys + rate limits before hitting live providers

# (Optional) Configure pilot rollout cohorts
# cp config/pilot_cohorts.example.json config/pilot_cohorts.json

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
3. Stage‑B selector (`gyre/selector.py`) runs knapsack + MMR, optionally biasing the order with the DSPy `RankCandidates` program (flag `dspy_selection`), and returns `selected`, `ledger`, `ranker` metadata, and trace so every token and millisecond is accounted for.
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
| `POST /sessions/register` | Register a session's tenant/project/user scope before observe/propose/inject. |
| `POST /patches/propose` | Run Stage A/B under explicit budgets; returns patch, scope echo, Stage‑A ledger, Stage‑B ledger, and trace. |
| `POST /patches/inject` | Inject a patch through the broker (requires prior consent). |
| `GET /review/candidates` / `POST /review/export_patch` / `GET /review/audit` | Reviewer workflow for manual CPP exports and audits. |
| `POST /governance/consent` | Record tenant/project/user consent. |
| `POST /transports/chaos` / `GET /transports/status` | Toggle transport availability and view health/cooldown metrics. |
| `GET /health/transports` | Summaries of transport availability, cooldowns, per tenant/project metrics, plus config coverage. |
| `GET /metrics/transports` | Per-transport SLA snapshot (success/failure counts, latency, last error). |
| `GET /metrics/observer` / `GET /metrics/dspy` | Observe→ingest telemetry plus Stage A/B token averages. |
| `GET /metrics/prometheus` | Prometheus scrape endpoint (all metrics). |
| `GET /feature_flags` / `POST /feature_flags` | Inspect or toggle runtime flags (e.g., DSPy logging). |
| `GET /skills` / `POST /skills/share` | List promoted skills (consent-gated) and share them with cohorts. |
| `POST /patches/feedback` / `GET /patches/feedback` | Hosts report accept/reject verdicts; reviewers inspect recent feedback + stats. |
| `GET /pilot/status` | Pilot rollout status (whether gating config is active). |

CLI helpers:
- `scripts/replay_session.py` — stream JSON/JSONL traces into `/observe/ingest`.
- `curl -X POST /sessions/register` — register tenant/project/user scopes before calling `/observe/ingest` or `/patches/propose`.
- `scripts/pipe_provider_events.py` — turn provider logs into ingest batches (`--provider openai|anthropic`).
- `scripts/reviewer_cli.py list|export` — inspect candidates and craft manual patches from the terminal.
- `scripts/evaluate_selection.py` — offline Stage A/B evaluation harness.
- `scripts/consolidate_graph.py` — prune stale nodes from the temporal graph (`--ttl-hours` defaults to 24) to keep persistence lean.
- `scripts/promote_skills.py` — promote high-signal nodes into the skill registry and sync them for sharing.
- `scripts/log_examples.py --log data/logs/propose.jsonl --out data/train` — extract DSPy training datasets (ranker inputs/outputs, summaries) from the `DatasetLogger` file.
- `scripts/build_dspy_datasets.py --log data/logs/propose.jsonl --out data/train` or `make datasets` — canonical Stage A/B dataset builder that emits `rank|sum|ev|red|blue_{train,eval}.jsonl` (includes host feedback weights when `data/feedback.jsonl` exists).
- `scripts/run_learning_cycle.sh [log] [data_dir]` — one-shot automation that builds datasets, compiles DSPy modules, and runs evaluation for the specified log. Respects `DSPY_ACCEPTED_WEIGHT`, `DSPY_REJECTED_WEIGHT`, `DSPY_DEFAULT_WEIGHT`, and `DSPY_NEGATIVE_SAMPLES` (or pass the equivalent flags to `scripts/build_dspy_datasets.py`) and writes `data/learning_cycle.json` (override with `LEARNING_META_PATH`) so Prometheus can track the last successful run.
- `scripts/gyre_cli.py` — Typer-based CLI (`uv run python scripts/gyre_cli.py --help`) that guides you through session registration, ingest/propose/inject flows, config validation, onboarding (auto-runs `validate-configs` unless `--no-validate`), learning-cycle automation, and transport health checks (rich summary by default, `--raw` for JSON) plus an interactive `guide` command. See `docs/CLI-UX.md` for usage and troubleshooting.
- `uv run python scripts/gyre_cli.py validate-configs --tenant demo --project pilot` validates your transports/pilot configs and prints actionable fixes.
- `scripts/compile_dspy.py` / `scripts/evaluate_dspy.py` — compile DSPy programs from logged datasets and summarize Stage A/B performance; CI runs these in mock mode on every push.
- `scripts/run_tests.sh` — deterministic test runner that prefers `.venv/bin/python -m pytest -q` and only falls back to `uv run` when no local venv exists.

### Dashboards & Health Checks
- Import `grafana/dashboards/gyre-pilot.json` into Grafana (see `docs/OBSERVABILITY.md`) to visualize selection tokens, transport latency/error rates, and pilot consent coverage; alert rules live in `scripts/prometheus/gyre.rules.yml`.
- Use `gyre transport-health` for a quick terminal view into `/health/transports` (availability, cooldowns, tenant/project stats); pass `--raw` when you need the JSON for automation.
- For pilot onboarding, run `gyre onboard-partner --tenant <name> --project <name>` and let the CLI immediately run `gyre validate-configs` so you see transport credential gaps before shipping configs.

---

## Development Workflow

1. **Docs First**: docs/PRD → docs/SPEC → docs/ARCHITECTURE → README/AGENTS. Align changes with the documents (open a beads issue if they diverge).
2. **Environment**: use `uv` for installs, but run tests via `make test` (which calls `scripts/run_tests.sh` → `.venv/bin/python -m pytest -q`) to avoid the current macOS SystemConfiguration panic that `uv run pytest -q` triggers inside the sandbox. The script also exports `DSPY_MOCK=1` and `GYRE_TRANSPORT_FORCE_STUB=1` so DSPy programs and transports stay in mock mode unless you explicitly opt in to real models. Secrets live in `.env`, and per-tenant transport credentials/rate limits live in `config/transports.json` (copy from the `.example` file and keep real keys out of git).
3. **Issue Tracking**: run `bd quickstart` for the Beads workflow. Create tasks (`bd create "feat"`), model dependencies (`bd dep add`), and keep statuses updated (`bd update issue --status in_progress`).  
4. **Coding Guidelines**: Python ≥3.10, type hints, four-space indent. Prefer composition over inheritance; update or create `tests/test_<module>.py` alongside code changes.
5. **Policies & Consent**: before testing injections, grant consent via `POST /governance/consent`. The policy engine rejects over-budget patches.

---

## Testing & Evaluation

- Unit/integration suite: `make test` (or `./scripts/run_tests.sh`) which uses the local `.venv/bin/python -m pytest -q` runner; this sidesteps the uv panic seen on macOS sandboxes while still honoring the same dependency set. The runner exports `DSPY_MOCK=1` and `GYRE_TRANSPORT_FORCE_STUB=1` so tests exercise the stubbed DSPy modules + transports without hitting real providers.  
  > `uv run pytest -q` currently panics (`system-configuration` crate can't create a dynamic store when sandboxed). Outside the sandbox you can keep using `uv run` directly.
- E2E smoke: run the dev server, replay a trace, request a patch, grant consent, and inject through a transport.
- Offline selection analysis: `scripts/evaluate_selection.py` surfaces Stage A/B ledger stats for any recorded trace.
- Chaos: `POST /transports/chaos` lets you simulate transport outages to ensure fallbacks + cooldowns behave.
- DSPy training workflow: `DSPY_MOCK=1 ./scripts/run_tests.sh` for fast unit coverage, `scripts/build_dspy_datasets.py --log data/logs/propose.jsonl --out data/train` to refresh training corpora, followed by `DSPY_MOCK=0 uv run python scripts/compile_dspy.py --data-dir data/train` and `uv run python scripts/evaluate_dspy.py --log data/logs/propose.jsonl` when you're ready to benchmark real models.
- Feedback weighting & negatives: set `DSPY_ACCEPTED_WEIGHT`, `DSPY_REJECTED_WEIGHT`, `DSPY_DEFAULT_WEIGHT`, and `DSPY_NEGATIVE_SAMPLES` (or pass the equivalent flags to `scripts/build_dspy_datasets.py`) to control how verdicts influence training data. Each successful learning cycle writes `data/learning_cycle.json`, powering the `gyre_learning_last_run_timestamp` Prometheus gauge.
- GitHub Actions `nightly-learning.yml` runs `scripts/run_learning_cycle.sh` on a 07:30 UTC cron with `LEARNING_REPORT_PATH=dist/learning/metrics.json`, then uploads `data/train/`, `data/dspy_cache/`, and `dist/learning/` artifacts so you can review dataset diffs and evaluation summaries in the Actions UI.
- Transport production workflow: copy `config/transports.example.json`, fill in tenant/project credentials + `rate_limit_per_min`, unset `GYRE_TRANSPORT_FORCE_STUB`, register sessions via `/sessions/register`, and monitor `/metrics/transports`, `/metrics/prometheus`, and `/transports/status` (scrape Prometheus using `scripts/prometheus/gyre.rules.yml` for sample alerts) while piloting with external hosts.

---

## Roadmap & References

- **M2**: Proactive CPP injection with transport broker, policy/redaction, consent, and chaos testing (all staged here).  
- **M3**: Temporal graph hardening, skill promotion, and cohort sharing (see `ARCHITECTURE.md`).  
- **M4**: Adaptive DSPy learning loops and automated evaluation harnesses.
- **M7 (in planning)**: Pilot readiness with multi-tenant transport configuration, SLA telemetry, and host feedback loops.

Research references: `RESEARCH-REFERENCES.md` aggregates the papers (ACE, DSPy, GraphRAG, etc.) that informed this design. Operational guidance lives in `docs/OBSERVABILITY.md` (Prometheus scraping, alert rules, and future OTel hooks). Pilot onboarding steps are in `docs/PILOT-ONBOARDING.md`. Nightly learning automation guidance is in `docs/LEARNING-AUTOMATION.md`.

---

Gyre is built to be extended: replace the stub transports with real ones, wire your observability stack into the telemetry endpoints, and iterate on the planner/selector using the evaluation harness. Contributions that keep efficacy-per-token high and policies airtight are welcome.
- `scripts/prometheus/gyre.rules.yml` — sample Prometheus alert rules for transport latency/error budgets, consent gaps, and stale learning cycles (copy into your infra if you’re monitoring pilots).
- `scripts/validate_pilot.py --config-dir config` — sanity-check `config/transports.json` and `config/pilot_cohorts.json` before enabling external pilots.
- `python scripts/onboard_partner.py --tenant <name> --project <name> --openai-key ...` — bootstrap pilot configs from the CLI (see `docs/PILOT-ONBOARDING.md`).
- Import `grafana/dashboards/gyre-pilot.json` into Grafana to visualize transport latency/error rates and selection tokens for each pilot tenant (run `make dashboards` to copy both the dashboard JSON and alert rules into `dist/observability/`).
