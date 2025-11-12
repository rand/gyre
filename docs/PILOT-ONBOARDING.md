# Pilot Onboarding Checklist

1. **Copy configs**
   ```bash
   python scripts/onboard_partner.py \
     --tenant acme \
     --project pilot \
     --openai-key sk-openai \
     --anthropic-key sk-anthropic \
     --gemini-key sk-gemini
   ```
   This writes `config/transports.json` and `config/pilot_cohorts.json` (creating the directory if needed). Prefer `uv run python scripts/gyre_cli.py onboard-partner --tenant acme --project pilot` to get guided prompts plus automatic `validate-configs`.

2. **Validate configs**
   ```bash
   python scripts/validate_pilot.py --config-dir config
   ```
   The script checks that every tenant/project has API keys, rate limits, and pilot enrollment.

3. **Register sessions**
   Call `/sessions/register` before ingesting or invoking `/patches/propose` so the transport broker and pilot gating use the correct tenant/project scope.

4. **Run health checks**
   - `./scripts/run_tests.sh` – ensures the full pipeline works locally (uses stubs by default).
   - `curl /metrics/transports` / `/metrics/prometheus` – confirm Prometheus scraping works and optionally import `scripts/prometheus/gyre.rules.yml` for alerts.

5. **Start pilot**
   With configs validated and sessions registered, replay traces via `scripts/replay_session.py`, request patches, and monitor `/transports/status` plus `/patches/feedback` to keep tabs on host responses.
