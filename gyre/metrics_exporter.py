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
        ["transport", "tenant"],
    )
    TRANSPORT_FAILURE = Counter(
        "gyre_transport_failure_total",
        "Transport failures",
        ["transport", "tenant"],
    )
    TRANSPORT_LATENCY = Histogram(
        "gyre_transport_latency_ms",
        "Transport latency in milliseconds",
        ["transport", "tenant"],
        buckets=(25, 50, 100, 200, 400, 800, 1600),
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


def record_transport_success(transport: str, tenant: str, latency_ms: float) -> None:
    if not Counter:
        return
    TRANSPORT_SUCCESS.labels(transport=transport, tenant=tenant).inc()
    TRANSPORT_LATENCY.labels(transport=transport, tenant=tenant).observe(latency_ms)


def record_transport_failure(transport: str, tenant: str) -> None:
    if not Counter:
        return
    TRANSPORT_FAILURE.labels(transport=transport, tenant=tenant).inc()
