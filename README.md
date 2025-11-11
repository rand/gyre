# Agentic Memory Supervisor (Gyre) — Starter

This repo is a buildable starter for a proactive, safe, efficient agentic memory service that can **observe** agent sessions and **inject** minimal context patches.

## Quickstart (Python with `uv`)

```bash
# Create env and install
uv venv
uv pip install -e .

# Copy env and set provider keys
cp .env.example .env
# export OPENAI_API_KEY=... etc

# Run dev server
uv run python server/run_dev_server.py

# Seed tiny training data and run DSPy light compiles
uv run python scripts/seed_datasets.py
```

## Layout
- `PRD.md`, `SPEC.md`, `ARCHITECTURE.md`, `RESEARCH-REFERENCES.md`
- `agentic_memory/` — code
- `data/train/` — tiny JSONL datasets for DSPy optimizers
- `tests/` — minimal tests
- `transports/` adapters for OpenAI, Anthropic, Gemini

## Documentation Stack
Follow the documents in this order when making design or implementation decisions:
1. `PRD.md` — source of truth for product goals and milestones.
2. `SPEC.md` — canonical APIs, schemas, and constraints derived from the PRD.
3. `ARCHITECTURE.md` — system design that satisfies the spec (update it whenever the spec changes).
4. `README.md` / `AGENTS.md` — contributor workflow, tooling, and local procedures.
If you spot conflicts, align with the higher-precedence document and open a beads issue describing the delta.

## Notes
- DSPy programs are wired with signatures and can be compiled later with MIPROv2/COPRO once you accumulate logs.
- Transports are stubs; wire them to your infra for real injection.
- Session taps now live in `gyre.taps`; use `scripts/replay_session.py --session demo --trace traces/example.jsonl` to stream a trace into the dev server. Provider-specific adapters (e.g., OpenAI Realtime) can call the same base helper and post to `/observe/ingest`.
- Provider ingestion helper: `scripts/pipe_provider_events.py` supports `--provider openai|anthropic` to translate raw provider logs into Gyre events.
- Reviewer endpoints: `GET /review/candidates`, `POST /review/export_patch`, and `GET /review/audit` power audits; `scripts/reviewer_cli.py` wraps these for quick CLI workflows when labeling data or showcasing Gyre.
- Observability: call `GET /metrics/observer` to inspect ingest counts/novelty stats while developing. Extend this instrumentation (or wire your own telemetry backend) before deploying to larger environments.
- Stage A planner: the dev server now runs a stub `DeferredQueryPlanner` before selection; inspect the `stage_a` field in `/patches/propose` responses or extend `gyre/planner.py` with your real query providers.
- Stage B selector: `/patches/propose` responses include a `ledger` (token/latency consumption) and `trace` (selected item gains) produced by the new budget-aware selector in `gyre/selector.py`.
- Slot composer: `gyre/composer.py` enforces per-slot caps and records token counts so manual/automatic patches share the same blueprint metadata; see `/review/export_patch` responses for examples.
- Evaluation harness: `scripts/evaluate_selection.py` replays recorded candidates through the planner + selector to surface ledger stats and selection traces before shipping changes.
- Transport broker: use `POST /patches/inject` (backed by `gyre/transports/broker.py`) to simulate sending CPP payloads through OpenAI/Anthropic/Gemini stubs; responses include transport acknowledgements for audit trails.
- Governance: register consent via `POST /governance/consent` before calling `/patches/inject`; the policy engine enforces token budgets and redaction rules (see `gyre/governance.py`) and audit events are persisted under `data/audit.log`.


> This distribution has been renamed to **Gyre**.
