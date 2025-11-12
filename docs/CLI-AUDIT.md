# CLI UX Audit

## Existing touchpoints
- `scripts/replay_session.py` — raw script, minimal argument validation, no guidance about registering scopes.
- `scripts/pipe_provider_events.py` — limited docs, no prompts.
- `scripts/validate_pilot.py` / `scripts/onboard_partner.py` — separate commands, no combined flow.
- `scripts/run_tests.sh` — hard-coded env vars, no options.

## Desired experience
1. `gyre` CLI guiding users through:
   - Registering session scopes.
   - Ingesting traces interactively (choose file, preview events).
   - Requesting patches with budget defaults.
   - Injecting patches with consent checks.
   - Validating configs.
2. Rich error messages with actionable suggestions (e.g., “config/transports.json missing; run `python scripts/onboard_partner.py ...`”).
3. Contextual help on every step (what data is needed, which command to run next).

## Gaps
- No single entry point; onboarding requires reading multiple docs.
- Error handling is inconsistent (raw tracebacks from CLI scripts).
- No interactive prompts or defaults beyond a few scripts.
- Lack of troubleshooting guide; need consolidated docs.
