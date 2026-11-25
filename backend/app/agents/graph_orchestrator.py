"""
LangGraph Multi-Agent Orchestrator — StateGraph workflow for discovery,
extraction, validation, deduplication, and notification.
"""

from contextlib import suppress
from typing import Any, TypedDict

import structlog
from langgraph.graph import END, START, StateGraph

from app.agents.discovery.crawler_agent import CrawlerAgent
from app.agents.discovery.query_generator import generate_search_queries
from app.agents.discovery.search_agent import SearchAgent
from app.agents.intelligence.extractor_agent import ExtractorAgent
from app.agents.intelligence.validator_agent import ValidatorAgent
from app.agents.tools.content_cleaner import truncate_for_llm
from app.agents.tools.rate_limiter import InMemoryRateLimiter
from app.models.schemas.agent import SearchResult
from app.models.schemas.opportunity import ExtractedOpportunity
from app.nlp.deadline_parser import parse_deadline
from app.nlp.keyword_extraction import analyze_text

logger = structlog.get_logger(__name__)


# ── LangGraph State Definition ──────────────────────


class DiscoveryState(TypedDict):
    """Pipeline state passed across LangGraph nodes."""

    topics: list[str]
    opportunity_types: list[str]
    max_urls: int
    queries: list[str]
    search_results: list[dict]
    crawled_pages: list[dict]
    extracted_opportunities: list[dict]
    validated_opportunities: list[dict]
    stored_count: int
    errors: list[str]
    status: str


# ── Node Implementations ────────────────────────────


async def generate_queries_node(state: DiscoveryState) -> dict[str, Any]:
    """Node 1: Generate targeted search queries."""
    topics = state.get("topics", [])
    types = state.get("opportunity_types", [])

    queries = generate_search_queries(
        topics=topics,
        opportunity_types=types if types else None,
        max_queries=10,
    )
    logger.info("graph_node_queries", count=len(queries))
    return {"queries": queries, "status": "queries_generated"}


async def search_node(state: DiscoveryState) -> dict[str, Any]:
    """Node 2: Search web engines."""
    queries = state.get("queries", [])
    search_agent = SearchAgent()
    results: list[SearchResult] = []

    for q in queries:
        try:
            res = await search_agent.search(query=q, max_results=5)
            results.extend(res)
        except Exception as e:
            logger.warning("search_node_failed", query=q[:50], error=str(e))

    await search_agent.close()

    # Deduplicate URLs
    seen = set()
    unique_results = []
    for r in results:
        if r.url not in seen:
            seen.add(r.url)
            unique_results.append(r.model_dump())

    max_urls = state.get("max_urls", 20)
    unique_results = unique_results[:max_urls]

    logger.info("graph_node_search", total_urls=len(unique_results))
    return {"search_results": unique_results, "status": "search_completed"}


async def crawl_node(state: DiscoveryState) -> dict[str, Any]:
    """Node 3: Crawl URLs and convert to markdown."""
    search_results = state.get("search_results", [])
    crawler = CrawlerAgent()
    rate_limiter = InMemoryRateLimiter()
    pages = []

    for item in search_results:
        url = item.get("url", "")
        try:
            await rate_limiter.wait_and_acquire_async(url)
            res = await crawler.crawl(url)
            if res.status_code == 200 and res.markdown:
                pages.append(
                    {
                        "url": url,
                        "title": res.title,
                        "markdown": res.markdown,
                    }
                )
        except Exception as e:
            logger.warning("crawl_node_failed", url=url[:60], error=str(e))

    await crawler.close()
    logger.info("graph_node_crawl", crawled=len(pages))
    return {"crawled_pages": pages, "status": "crawl_completed"}


async def extract_node(state: DiscoveryState) -> dict[str, Any]:
    """Node 4: LLM extraction + NLP enrichment."""
    pages = state.get("crawled_pages", [])
    extractor = ExtractorAgent()
    all_extracted = []

    for page in pages:
        nlp_result = analyze_text(page["markdown"])
        if not nlp_result.is_opportunity:
            continue

        try:
            extracted_list = await extractor.extract(
                content=truncate_for_llm(page["markdown"]),
                url=page["url"],
                title=page["title"],
            )

            for opp in extracted_list:
                if not opp.required_skills:
                    opp.required_skills = nlp_result.skills
                if not opp.programming_languages:
                    opp.programming_languages = nlp_result.programming_languages
                if not opp.research_areas:
                    opp.research_areas = nlp_result.research_areas
                if not opp.opportunity_type and nlp_result.opportunity_type_hint:
                    opp.opportunity_type = nlp_result.opportunity_type_hint
                if not opp.deadline and nlp_result.deadline_str:
                    opp.deadline = parse_deadline(nlp_result.deadline_str)
                opp.raw_text = page["markdown"][:5000]

                all_extracted.append(opp.model_dump())
        except Exception as e:
            logger.warning("extract_node_failed", url=page["url"][:60], error=str(e))

    logger.info("graph_node_extract", extracted=len(all_extracted))
    return {"extracted_opportunities": all_extracted, "status": "extraction_completed"}


async def validate_node(state: DiscoveryState) -> dict[str, Any]:
    """Node 5: Quality & authenticity validation."""
    extracted_dicts = state.get("extracted_opportunities", [])
    validator = ValidatorAgent()
    valid_list = []

    for opp_dict in extracted_dicts:
        try:
            opp = ExtractedOpportunity(**opp_dict)
            report = await validator.validate(opp)
            if report.is_valid:
                opp.confidence_score = min(
                    opp.confidence_score,
                    report.authenticity_score,
                )
                valid_list.append(opp.model_dump())
        except Exception as e:
            logger.warning("validate_node_failed", error=str(e))

    logger.info("graph_node_validate", valid=len(valid_list))
    return {"validated_opportunities": valid_list, "status": "validation_completed"}


async def store_node(state: DiscoveryState) -> dict[str, Any]:
    """Node 6: Database storage & vector/graph ingestion."""
    valid_dicts = state.get("validated_opportunities", [])
    from app.core.database import async_session_factory
    from app.services.opportunity_service import OpportunityService
    from app.workers.embedding_worker import embed_opportunity

    stored = 0
    async with async_session_factory() as db:
        service = OpportunityService(db)

        for opp_dict in valid_dicts:
            opp = ExtractedOpportunity(**opp_dict)

            # A source page can contain multiple distinct openings; dedup by listing identity.
            existing = await service.find_by_title_and_org(opp.title, opp.organization)
            if existing:
                continue

            db_opp = await service.create_from_extraction(opp)
            stored += 1

            # Dispatch embedding + KG worker
            with suppress(Exception):
                embed_opportunity.delay(str(db_opp.id))

        await db.commit()

    logger.info("graph_node_store", stored=stored)
    return {"stored_count": stored, "status": "pipeline_completed"}


# ── Conditional Routing Functions ───────────────────


def should_crawl(state: DiscoveryState) -> str:
    """Check if search produced URLs to crawl."""
    results = state.get("search_results", [])
    if results:
        return "crawl"
    logger.info("routing_end_no_search_results")
    return END


def should_extract(state: DiscoveryState) -> str:
    """Check if crawl produced pages."""
    pages = state.get("crawled_pages", [])
    if pages:
        return "extract"
    logger.info("routing_end_no_crawled_pages")
    return END


# ── Build LangGraph Workflow ────────────────────────


def build_discovery_graph():
    """Build and compile the LangGraph StateGraph for discovery."""
    workflow = StateGraph(DiscoveryState)

    # Add nodes
    workflow.add_node("generate_queries", generate_queries_node)
    workflow.add_node("search", search_node)
    workflow.add_node("crawl", crawl_node)
    workflow.add_node("extract", extract_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("store", store_node)

    # Add edges
    workflow.add_edge(START, "generate_queries")
    workflow.add_edge("generate_queries", "search")
    workflow.add_conditional_edges("search", should_crawl, ["crawl", END])
    workflow.add_conditional_edges("crawl", should_extract, ["extract", END])
    workflow.add_edge("extract", "validate")
    workflow.add_edge("validate", "store")
    workflow.add_edge("store", END)

    return workflow.compile()


class LangGraphOrchestrator:
    """LangGraph orchestrator interface."""

    def __init__(self):
        self.graph = build_discovery_graph()

    async def run(
        self,
        topics: list[str],
        opportunity_types: list[str] | None = None,
        max_urls: int = 20,
    ) -> dict[str, Any]:
        """Execute the LangGraph discovery workflow."""
        initial_state: DiscoveryState = {
            "topics": topics,
            "opportunity_types": opportunity_types or [],
            "max_urls": max_urls,
            "queries": [],
            "search_results": [],
            "crawled_pages": [],
            "extracted_opportunities": [],
            "validated_opportunities": [],
            "stored_count": 0,
            "errors": [],
            "status": "started",
        }

        final_state = await self.graph.ainvoke(initial_state)

        return {
            "topics": topics,
            "status": final_state.get("status"),
            "queries_count": len(final_state.get("queries", [])),
            "search_urls": len(final_state.get("search_results", [])),
            "pages_crawled": len(final_state.get("crawled_pages", [])),
            "extracted": len(final_state.get("extracted_opportunities", [])),
            "validated": len(final_state.get("validated_opportunities", [])),
            "stored_count": final_state.get("stored_count", 0),
        }
