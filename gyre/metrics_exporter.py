from __future__ import annotations

try:
    from prometheus_client import Counter, Gauge, Histogram
except ImportError:  # pragma: no cover - fallback when dependency missing
    Counter = Gauge = Histogram = None  # type: ignore

if Counter:
    OBSERVE_EVENTS = Counter(
        "gyre_observe_events_total",
        "Total number of events processed by /observe/ingest",
        ["tenant"],
    )
    OBSERVE_TOKENS = Counter(
        "gyre_observe_tokens_total",
        "Total tokens estimated during observation",
        ["tenant"],
    )
    SELECTION_TOKENS = Gauge(
        "gyre_selection_tokens_last",
        "Last Stage B tokens used",
        ["tenant"],
    )
    TRANSPORT_SUCCESS = Counter(
        "gyre_transport_success_total",
        "Transport successes",
        ["transport", "tenant", "project"],
    )
    TRANSPORT_FAILURE = Counter(
        "gyre_transport_failure_total",
        "Transport failures",
        ["transport", "tenant", "project"],
    )
    TRANSPORT_LATENCY = Histogram(
        "gyre_transport_latency_ms",
        "Transport latency in milliseconds",
        ["transport", "tenant", "project"],
        buckets=(25, 50, 100, 200, 400, 800, 1600),
    )
    CONSENT_MISSING = Counter(
        "gyre_consent_missing_total",
        "Number of patch injections blocked due to missing consent",
        ["tenant", "project"],
    )
    LEARNING_LAST_RUN = Gauge(
        "gyre_learning_last_run_timestamp",
        "Unix timestamp of the last successful learning cycle",
        [],
    )


def record_observe(tenant: str, events: int, tokens: int) -> None:
    if not Counter:
        return
    OBSERVE_EVENTS.labels(tenant=tenant).inc(events)
    OBSERVE_TOKENS.labels(tenant=tenant).inc(tokens)


def record_selection(tenant: str, tokens_used: int) -> None:
    if not Counter:
        return
    SELECTION_TOKENS.labels(tenant=tenant).set(tokens_used)


def _project_label(project: str | None) -> str:
    return project or "default"


def record_transport_success(transport: str, tenant: str, project: str | None, latency_ms: float) -> None:
    if not Counter:
        return
    label = _project_label(project)
    TRANSPORT_SUCCESS.labels(transport=transport, tenant=tenant, project=label).inc()
    TRANSPORT_LATENCY.labels(transport=transport, tenant=tenant, project=label).observe(latency_ms)


def record_transport_failure(transport: str, tenant: str, project: str | None) -> None:
    if not Counter:
        return
    label = _project_label(project)
    TRANSPORT_FAILURE.labels(transport=transport, tenant=tenant, project=label).inc()


def record_missing_consent(tenant: str, project: str | None) -> None:
    if not Counter:
        return
    CONSENT_MISSING.labels(tenant=tenant, project=_project_label(project)).inc()


def record_learning_last_run(timestamp: float) -> None:
    if not Counter:
        return
    LEARNING_LAST_RUN.set(timestamp)
