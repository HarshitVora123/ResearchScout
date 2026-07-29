"""Unit tests for Phase 5 — Prometheus Metrics & OAuth2 Integration."""

import pytest

from app.core.metrics import (
    AGENT_EXECUTIONS_TOTAL,
    HTTP_REQUESTS_TOTAL,
    OPPORTUNITIES_DISCOVERED_TOTAL,
    metrics_endpoint,
)
from app.core.oauth import OAuth2Service


class TestPrometheusMetrics:
    """Test metrics counters and /metrics response generator."""

    def test_metrics_counters_increment(self):
        HTTP_REQUESTS_TOTAL.labels(method="GET", endpoint="/health", status_code="200").inc()
        OPPORTUNITIES_DISCOVERED_TOTAL.labels(source_type="university").inc()
        AGENT_EXECUTIONS_TOTAL.labels(agent_name="LangGraphOrchestrator", status="success").inc()

        res = metrics_endpoint()
        assert res.status_code == 200
        assert b"http_requests_total" in res.body
        assert b"opportunities_discovered_total" in res.body


class TestOAuth2Service:
    """Test OAuth2 token verification fallbacks."""

    @pytest.mark.asyncio
    async def test_invalid_google_token_returns_none(self):
        oauth = OAuth2Service()
        profile = await oauth.verify_google_token("invalid_token")
        assert profile is None

    @pytest.mark.asyncio
    async def test_invalid_github_token_returns_none(self):
        oauth = OAuth2Service()
        profile = await oauth.verify_github_token("invalid_token")
        assert profile is None
