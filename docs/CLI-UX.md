# Gyre CLI Guide

## Commands
- `gyre register-session <session> <tenant> <project> <user>`
- `gyre ingest <session> <trace>`
- `gyre propose <session> <task_desc> [--tokens 800 --latency-ms 800]`
- `gyre inject <patch.json> [--transport best]`
- `gyre validate-configs [--config-dir config]`
- `gyre give-consent <tenant> <project> <user>` / `--no-consent`
- `gyre transport-health` — interactive `/health/transports` summary (`--raw` prints JSON).
- `gyre onboard-partner --tenant <t> --project <p> --openai-key ... [--no-validate]` (wraps onboarding script and runs `validate-configs` unless suppressed)
- `gyre learning-cycle [--log path --data-dir path --feedback path]`
- `gyre guide` – prompts through the above steps interactively.

## Quickstart Walkthrough
1. `uv run python scripts/gyre_cli.py guide` – guided prompts walk you through registering a session, ingesting a trace (defaults to `traces/example.jsonl`), and generating a patch. The command echoes each API call and stops before injection so you can review the patch body.
2. `uv run python scripts/gyre_cli.py transport-health` – prints availability, cooldowns, and per tenant/project stats sourced from `/health/transports`; add `--raw` when you want machine-readable JSON for your own dashboards.
3. `uv run python scripts/gyre_cli.py onboard-partner --tenant acme --project pilot --openai-key sk-...` – writes `config/transports.json` + `config/pilot_cohorts.json`, then automatically runs `gyre validate-configs --tenant acme --project pilot` so you immediately see missing credentials/rate-limits. Pass `--no-validate` if you need to defer checks (not recommended).
4. `uv run python scripts/gyre_cli.py learning-cycle --log data/logs/propose.jsonl --data-dir data/train` – runs the same automation as the nightly workflow, rebuilding datasets under `data/train/`, recompiling DSPy modules, and printing evaluation stats (set `LEARNING_REPORT_PATH` to capture them to disk).

## Error handling
- All HTTP failures print the status code and response body before exiting with code 1.
- Missing or invalid trace/patch files are detected before any HTTP call, with actionable messages (`File not found` / `Failed to parse JSON`).
- Subprocess failures (onboarding, learning-cycle, validators) surface the captured stderr plus exit code.
- Set `GYRE_BASE_URL` to point at non-default deployments.

## Troubleshooting
- “403 Pilot rollout disabled”: confirm `config/pilot_cohorts.json` allows the tenant/project.
- “401 Consent required”: call `/governance/consent` or use the CLI once consent endpoints are exposed.
- "Connection refused": ensure `uv run python server/run_dev_server.py` is running and `GYRE_BASE_URL` is correct.
- "Pilot disabled" or "rate limit": run `gyre transport-health` and `gyre validate-configs --tenant ...` to inspect configs.
- "Learning stale" alert: inspect the `Nightly Learning` workflow artifacts or run `gyre learning-cycle --log data/logs/propose.jsonl --data-dir data/train` locally; confirm `data/learning_cycle.json` updates and re-check Prometheus for `gyre_learning_last_run_timestamp`.
