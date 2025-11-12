# Repository Guidelines

## Project Structure & Module Organization
Source lives in `gyre/`, split by responsibility (`selector.py`, `retriever.py`, transports, stores, `taps/` adapters). FastAPI orchestration sits in `server/` via `server/run_dev_server.py`. Shared utilities (dataset seeding, maintenance jobs, trace replay) are under `scripts/`. Tests belong in `tests/` and mirror the package they cover (e.g., `tests/test_selector.py`). Strategy docs live in `docs/ARCHITECTURE.md`, `docs/PRD.md`, and `docs/SPEC.md`—skim them before touching flows.

## Build, Test, and Development Commands
Use `uv` for every workflow to keep dependencies reproducible:
- `uv venv && uv pip install -e .` bootstraps a local environment.
- `uv run python server/run_dev_server.py` (or `make run`) starts the FastAPI dev server with hot reload.
- `make test` (or `./scripts/run_tests.sh`) runs the suite via `.venv/bin/python -m pytest -q` with `DSPY_MOCK=1` and `GYRE_TRANSPORT_FORCE_STUB=1`, avoiding both the macOS SystemConfiguration panic and accidental real transport calls.
- `uv run python scripts/seed_datasets.py` (or `make seed`) refreshes `data/train/` so DSPy optimizers have sample traces.
- `cp config/transports.example.json config/transports.json` before piloting so each tenant/project has explicit provider keys + `rate_limit_per_min` entries (keep the real file out of git; leave `GYRE_TRANSPORT_FORCE_STUB=1` on if you want to remain offline).
- `cp config/pilot_cohorts.example.json config/pilot_cohorts.json` if you need rollout gating; scopes outside the allowlist will receive 403s from `/patches/propose` and `/patches/inject`.
- `uv run python scripts/replay_session.py --session demo --trace traces/example.jsonl` replays saved traces through `/observe/ingest`.
- `curl -X POST /sessions/register` (or similar) should be called before ingest/propose/inject so each session is associated with the correct tenant/project/user scope.
- `uv run python scripts/pipe_provider_events.py --provider openai --session demo --trace logs/openai.jsonl` converts provider logs (OpenAI/Anthropic) into ingest events.
- `uv run python scripts/reviewer_cli.py list --session demo` lists recent candidates; `... export --session demo --candidates <ids>` emits manual CPP blueprints.
- `uv run python scripts/reviewer_cli.py export --session demo --candidates evt:demo:1,evt:demo:2` captures manual CPP payloads after Stage A/B selection.
- `uv run python scripts/evaluate_selection.py --trace traces/example.json --budget-tokens 800 --budget-latency 800` replays recorded candidates through the planner/selector pipeline and reports ledger stats.
- `uv run python scripts/promote_skills.py --min-references 3` promotes high-signal nodes into the skill registry; pair with the `GET /skills` / `POST /skills/share` endpoints to debug cohort sharing.
- `DSPY_MOCK=1 uv run python scripts/compile_dspy.py --data-dir data/train` compiles DSPy modules against logged datasets; follow with `uv run python scripts/evaluate_dspy.py --log data/logs/propose.jsonl` to inspect Stage A/B averages.
- `scripts/build_dspy_datasets.py --log data/logs/propose.jsonl --out data/train` (or `make datasets`) materializes canonical datasets (`rank|sum|ev|red|blue_{train,eval}.jsonl`) before you compile DSPy modules; check the JSON summary for coverage ratios.
- Feature flags live in `data/feature_flags.json` and can be toggled via `POST /feature_flags?name=dspy_logging&value=false` (used to pause logging or enable DSPy injections); set `dspy_selection=true` to route Stage B ordering through the DSPy ranker.
- `POST /patches/inject` (or call via `curl`/tools) exercises the transport broker; pass `{"patch": {...}, "transport": "openai"}` using patches produced by `/patches/propose`.

## Documentation Stack & Precedence
Treat the documents as a cascade for intent and implementation detail:
- `docs/PRD.md` (current vision) defines *why* and the business outcomes. This takes precedence over all other local docs.
- `docs/SPEC.md` translates the PRD into APIs, schemas, and constraints. If a spec contradicts architecture/code, update the spec first.
- `docs/ARCHITECTURE.md` explains how we intend to fulfill the spec; adjust it whenever the design drifts.
- `README.md` and this guide capture contributor workflows; keep them synced after spec/architecture edits.
When in doubt, escalate differences instead of silently diverging—link beads issues to the doc/section you plan to change.

## Coding Style & Naming Conventions
Code targets Python ≥3.10 with 4-space indentation, type hints, and descriptive docstrings for public functions and DSPy signatures. Use `snake_case` for functions/variables, `PascalCase` for Pydantic models, and keep module names short and thematic (e.g., `observer.py`). Prefer composition over inheritance; keep DSPy programs declarative inside `gyre/programs.py`. Run `uv run pytest` before pushing; no formatter is enforced, so stay Black-compatible.

## Testing Guidelines
Write Pytest tests beside related modules (`tests/test_<module>.py`) and cover both high-confidence paths and constraint edges (token caps, latency budgets, governance filters). When adding a new selector or retriever strategy, create targeted fixtures rather than mocking everything. Keep assertions semantic (e.g., compare IDs or structured dicts) to avoid brittle float checks. Update or seed minimal datasets if tests rely on serialized memory objects.
- The test runner exports `DSPY_MOCK=1` and `GYRE_TRANSPORT_FORCE_STUB=1`, so DSPy programs and transports use the lightweight stubs. When validating against real providers, explicitly unset those variables, fill `config/transports.json`, and regenerate datasets via `scripts/build_dspy_datasets.py`.

## Commit & Pull Request Guidelines
The repo has no public history yet; adopt Conventional Commits (`feat:`, `fix:`, `chore:`) so future automation stays predictable. Keep commits self-contained with matching tests and a clear “why.” Pull requests should link relevant PRD/SPEC sections, summarize user-visible outcomes, list test commands (`uv run pytest -q`, etc.), and attach screenshots or JSON samples when touching transports or APIs. Keep diffs focused; spin off follow-up issues for speculative work.

## Planning & Issue Tracking (Beads)
We track implementation with [Beads](https://github.com/steveyegge/beads); the SQLite db lives in `.beads/beads.db`. Key commands:
- `bd quickstart` or `bd onboard` to review usage basics; `bd status` for a high-level dashboard.
- `bd create "Title"` opens an issue (IDs look like `gyre-1`). Use `--labels`, `--description`, or provide a markdown file for bulk creation.
- `bd list --open`, `bd show gyre-3`, and `bd ready` help triage work; `bd comment gyre-3 -m "..."`
  logs discussions.
- Model dependencies explicitly: `bd dep add gyre-3 gyre-1` marks gyre-3 as blocked until gyre-1 closes.
- Update state with `bd update gyre-1 --status in-progress` (accepted statuses: open, in-progress, blocked, closed) and keep summaries fresh.
- After any mutation run `bd status` (or `bd sync` if collaborating via git) so JSONL exports stay in lockstep.
Avoid editing `.beads` artifacts manually; always use `bd` commands so audits remain trustworthy.

## Environment & Configuration Tips
Copy `.env.example` → `.env` and fill provider keys (OpenAI, Anthropic, etc.) before hitting external transports. Never commit secrets or real trace data—add them to local `.env` or vault tooling. Use `PYTHONPATH=.` when running bespoke scripts so relative imports resolve, and prefer `uv run` over `python` to ensure the virtualenv is honored.

## Reviewer & Manual Patch Workflow
- Inspect recently ingested candidates via `GET /review/candidates?session_id=<id>`.
- Trigger manual CPP exports by POSTing to `/review/export_patch` with candidate IDs, slot specs, and optional reviewer notes; the endpoint returns a ready-to-use blueprint payload.
- Reviewers can also call `GET /review/audit` (or use `scripts/reviewer_cli.py`) to see the manual patches that have been exported and their provenance.
- Use these endpoints together with the tap/replay utilities to label data, audit provenance, and build DSPy training corpora.

## Telemetry & Metrics
- `GET /metrics/observer` exposes aggregate ingest stats (calls, events processed, novelty, token counts) for quick health checks during development.
- Extend this endpoint (or hook OpenTelemetry exporters) whenever you add new pipelines so dashboards stay accurate. Remember to add tests when metrics change.

## Stage A Query Planner
- `gyre/planner.py` currently houses a stub `DeferredQueryPlanner` that generates `deferred_query` candidates and executes the highest EV ones inside `/patches/propose` (see `stage_a` field in responses).
- Plug in your own provider-specific planners/executors before moving to production; ensure executed tool results are upserted into `PrivateStore`/graph and logged for evaluation harnesses.

## Stage B Selection
- `gyre/selector.py` now returns a structure with `selected`, `ledger`, and `trace`. The ledger tracks token/latency consumption plus risk bounds, and the trace shows marginal gains per candidate to simplify debugging.
- When integrating new selection strategies, keep the ledger accurate—`/patches/propose` surfaces it directly to reviewers, and tests (`tests/test_selector.py`) guard budget regressions.
- `gyre/composer.py` consumes selection output and produces slot-aware blueprints (with per-slot token counts) used by both the proactive `/patches/propose` flow and the reviewer CLI. Extend the fragments builder when adding new slots.
- Offline evaluation: use `scripts/evaluate_selection.py` (and `tests/test_evaluate_selection.py` as a reference) to measure Stage A/B ledgers before rolling out selector/planner changes.
- Transport broker: `gyre/transports/broker.py` routes CPP payloads through the stub OpenAI/Anthropic/Gemini adapters with simple retries; extend it when wiring real transports. Keep audit coverage by logging `/patches/inject` responses.
- Consent & Audit: use `POST /governance/consent` to grant per-scope approvals before injecting patches. Audit entries are appended to `data/audit.log` (see `gyre/audit.py`) and surfaced via `GET /review/audit` for reviewer workflows.
- Chaos endpoints: hit `POST /transports/chaos` with `{"transport":"openai","available":false}` to simulate failures and verify fallbacks; `GET /transports/status` shows counters/cooldowns so you can trace health during integration tests.
