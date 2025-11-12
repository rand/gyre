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
3. Dashboards: plot `gyre_transport_latency_ms_*`, `gyre_transport_failure_total`, and `gyre_selection_tokens_last` in Grafana to monitor pilot cohorts.

## OpenTelemetry (future work)

We currently emit structured metrics only. If you need spans, wrap the transport broker in OTLP exporters (see `gyre/transports/broker.py`) and emit spans whenever `record_transport_failure` is invoked.
