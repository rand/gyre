# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2025-11-12

### Added
- Scope-aware `/patches/propose` responses, dataset logging, and per tenant/project transport metrics plus `/health/transports` endpoint with CLI support.
- Nightly learning automation workflow (`.github/workflows/nightly-learning.yml`) that runs `scripts/run_learning_cycle.sh`, archives datasets, and uploads evaluation artifacts.
- Feedback-weighted dataset builder controls (verdict weights, deterministic negative sampling) with CLI flags/env vars and new Prometheus gauges for the last learning run plus consent-missing counters/alerts.
- CLI quickstart walkthrough, improved error handling, automatic onboarding validation, and transport-health summaries for `scripts/gyre_cli.py`.
- Prometheus alert rules for latency, error budgets, consent gaps, and stale learning cycles, alongside updated observability/pilot onboarding docs.

### Fixed
- Addressed missing scope propagation in patches/datasets, ensuring governance policies and dataset logs align.
- Hardened transport telemetry and metrics export so dashboards reflect cooldowns, availability, and scope-level SLA stats.

### Testing
- `uv run python -m pytest -q`
