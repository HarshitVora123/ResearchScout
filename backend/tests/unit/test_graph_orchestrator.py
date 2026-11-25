"""Unit tests for Phase 4 — LangGraph Multi-Agent Orchestrator."""

import pytest

from app.agents.graph_orchestrator import (
    build_discovery_graph,
    generate_queries_node,
    should_crawl,
    should_extract,
)


class TestLangGraphOrchestrator:
    """Test LangGraph StateGraph nodes and routing logic."""

    @pytest.mark.asyncio
    async def test_generate_queries_node(self):
        state = {
            "topics": ["NLP", "Computer Vision"],
            "opportunity_types": ["PhD"],
            "max_urls": 10,
        }
        res = await generate_queries_node(state)
        assert "queries" in res
        assert len(res["queries"]) > 0
        assert res["status"] == "queries_generated"

    def test_routing_should_crawl(self):
        # Has search results -> crawl
        state_with_results = {"search_results": [{"url": "https://mit.edu/phd"}]}
        assert should_crawl(state_with_results) == "crawl"

        # No search results -> __end__
        state_empty = {"search_results": []}
        assert should_crawl(state_empty) == "__end__"

    def test_routing_should_extract(self):
        state_with_pages = {"crawled_pages": [{"url": "https://mit.edu", "markdown": "content"}]}
        assert should_extract(state_with_pages) == "extract"

        state_empty = {"crawled_pages": []}
        assert should_extract(state_empty) == "__end__"

    def test_build_graph_structure(self):
        graph = build_discovery_graph()
        assert graph is not None
