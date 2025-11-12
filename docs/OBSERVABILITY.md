# Observability & Alerting

## Prometheus

1. Expose metrics: hit `GET /metrics/prometheus` (enabled once `prometheus-client` is installed) and scrape from Prometheus using something like:
   ```yaml
   scrape_configs:
     - job_name: "gyre"
       static_configs:
         - targets: ["gyre-dev:8000"]
   ```
2. Alert rules: copy `scripts/prometheus/gyre.rules.yml` to your infrastructure repo and reference it from the Prometheus server. The rules include latency and error budget alerts per transport/tenant; tune the thresholds to match your SLAs before pilot.
3. Dashboards: import `grafana/dashboards/gyre-pilot.json` into Grafana (run `make dashboards` to copy it plus the alert rules into `dist/observability/`) and customize it with any additional panels you need per tenant/project.

### Dashboard Walkthrough
1. Run `uv run python scripts/gyre_cli.py transport-health --raw > dist/observability/transport-health.json` to capture the latest `/health/transports` payload (availability, cooldowns, per-scope stats). Point the “Transport Health Summary” panel at that JSON or ingest it via a lightweight scraper.
2. `make dashboards` copies `grafana/dashboards/gyre-pilot.json` and `scripts/prometheus/gyre.rules.yml` into `dist/observability/`; upload the dashboard JSON through Grafana’s “Import” dialog, then adjust the data source name to match your Prometheus instance.
3. Configure alerts by applying `scripts/prometheus/gyre.rules.yml` and wiring notifications for:
   - `gyre_transport_failure_total` (per tenant/project) spikes.
   - `gyre_transport_latency_ms` p90 above your SLA.
   - Stale learning runs: add a rule on the custom metric that the nightly workflow emits via `dist/learning/metrics.json` (last updated timestamp).
4. Keep a CLI runbook handy: `gyre transport-health` for real-time triage, `gyre validate-configs --tenant ... --project ...` to verify credentials when the dashboard flags gaps, and `gyre learning-cycle` to manually re-run the evaluation loop if alerts fire.

## Alert Runbook
- **GyreTransportHighLatency / GyreTransportErrorBudget**: Run `gyre transport-health` to confirm cooldowns, then `gyre validate-configs --tenant <id>` if tenant-specific. Use Grafana’s per-tenant latency/error panels to narrow down providers.
- **GyreConsentMissing**: Triggered when `/patches/inject` is blocked for a tenant/project. Use `gyre give-consent <tenant> <project> <user>` or rerun onboarding if configs drifted. Cross-check `config/pilot_cohorts.json` to ensure the pilot isn’t gated.
- **GyreLearningStale**: No successful learning cycle in >6h. Inspect GitHub Actions `Nightly Learning` run logs or run `gyre learning-cycle --log ...` locally; confirm `data/learning_cycle.json` updates and the Prometheus gauge `gyre_learning_last_run_timestamp` moves.

## OpenTelemetry (future work)

We currently emit structured metrics only. If you need spans, wrap the transport broker in OTLP exporters (see `gyre/transports/broker.py`) and emit spans whenever `record_transport_failure` is invoked.
