"""
Prometheus Metrics & Observability — request counters, agent metrics, and latency histograms.
"""

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

# ── Metrics Definitions ──────────────────────────────

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests handled",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)

OPPORTUNITIES_DISCOVERED_TOTAL = Counter(
    "opportunities_discovered_total",
    "Total opportunities discovered by pipeline",
    ["source_type"],
)

AGENT_EXECUTIONS_TOTAL = Counter(
    "agent_executions_total",
    "Total AI agent executions",
    ["agent_name", "status"],
)

AGENT_EXECUTION_SECONDS = Histogram(
    "agent_execution_seconds",
    "Agent execution time in seconds",
    ["agent_name"],
)


def metrics_endpoint() -> Response:
    """FastAPI endpoint to export Prometheus metrics."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
