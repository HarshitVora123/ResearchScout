"""
LangGraph Discovery Pipeline — orchestrates the full search → crawl → extract → store flow.

This is the main orchestration layer that chains agents together into a
directed graph with conditional edges and state management.
"""

import uuid
from datetime import UTC, datetime

import structlog

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


class DiscoveryPipeline:
    """
    Orchestrates the full opportunity discovery pipeline.

    Pipeline flow:
    ┌──────────┐    ┌──────────┐    ┌───────────┐    ┌───────────┐    ┌──────────┐
    │  Query   │ →  │  Search  │ →  │   Crawl   │ →  │  Extract  │ →  │ Validate │ → Store
    │Generator │    │  Agent   │    │   Agent   │    │   Agent   │    │  Agent   │
    └──────────┘    └──────────┘    └───────────┘    └───────────┘    └──────────┘

    Can be run:
    - As an async pipeline (for real-time discovery from API)
    - As Celery tasks (for scheduled batch discovery)
    """

    def __init__(self) -> None:
        self.search_agent = SearchAgent()
        self.crawler_agent = CrawlerAgent()
        self.extractor = ExtractorAgent()
        self.validator = ValidatorAgent()
        self.rate_limiter = InMemoryRateLimiter()

    async def run(
        self,
        topics: list[str],
        opportunity_types: list[str] | None = None,
        max_urls: int = 20,
        search_engines: list[str] | None = None,
    ) -> dict:
        """
        Execute the full discovery pipeline for given topics.

        Args:
            topics: Research areas to search for
            opportunity_types: Specific types (PhD, Internship, etc.)
            max_urls: Maximum URLs to crawl
            search_engines: Which search APIs to use

        Returns:
            Pipeline execution summary with counts and results.
        """
        pipeline_id = str(uuid.uuid4())[:8]
        start = datetime.now(UTC)

        logger.info(
            "pipeline_started",
            pipeline_id=pipeline_id,
            topics=topics,
            types=opportunity_types,
        )

        # ── Step 1: Generate search queries ──────
        queries = generate_search_queries(
            topics=topics,
            opportunity_types=opportunity_types,
            max_queries=15,
        )
        logger.info("queries_generated", count=len(queries))

        # ── Step 2: Execute searches ─────────────
        all_results: list[SearchResult] = []
        for query in queries:
            try:
                results = await self.search_agent.search(
                    query=query,
                    engines=search_engines or ["google", "bing", "tavily"],
                    max_results=5,
                )
                all_results.extend(results)
            except Exception as e:
                logger.warning("search_failed", query=query[:60], error=str(e))

        # Deduplicate URLs
        seen_urls: set[str] = set()
        unique_urls: list[str] = []
        for result in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_urls.append(result.url)

        unique_urls = unique_urls[:max_urls]
        logger.info("search_complete", total_results=len(all_results), unique_urls=len(unique_urls))

        # ── Step 3: Crawl URLs ───────────────────
        crawled_pages: list[dict] = []
        for url in unique_urls:
            try:
                await self.rate_limiter.wait_and_acquire_async(url)
                crawl_result = await self.crawler_agent.crawl(url)

                if crawl_result.status_code == 200 and crawl_result.markdown:
                    crawled_pages.append(
                        {
                            "url": url,
                            "title": crawl_result.title,
                            "markdown": crawl_result.markdown,
                        }
                    )
            except Exception as e:
                logger.warning("crawl_failed", url=url[:100], error=str(e))

        logger.info("crawl_complete", crawled=len(crawled_pages))

        # ── Step 4: NLP filter + Extract ─────────
        all_extracted: list[ExtractedOpportunity] = []
        for page in crawled_pages:
            # NLP pre-filter
            nlp_result = analyze_text(page["markdown"])
            if not nlp_result.is_opportunity:
                continue

            # LLM extraction
            try:
                extracted = await self.extractor.extract(
                    content=truncate_for_llm(page["markdown"]),
                    url=page["url"],
                    title=page["title"],
                )

                # Enrich with NLP data
                for opp in extracted:
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

                all_extracted.extend(extracted)
            except Exception as e:
                logger.warning("extraction_failed", url=page["url"][:100], error=str(e))

        logger.info("extraction_complete", extracted=len(all_extracted))

        # ── Step 5: Validate ─────────────────────
        validated: list[ExtractedOpportunity] = []
        rejected = 0

        for opp in all_extracted:
            try:
                report = await self.validator.validate(opp)
                if report.is_valid:
                    opp.confidence_score = min(
                        opp.confidence_score,
                        report.authenticity_score,
                    )
                    validated.append(opp)
                else:
                    rejected += 1
                    logger.debug(
                        "validation_rejected",
                        title=opp.title[:60],
                        issues=report.issues[:3],
                    )
            except Exception as e:
                logger.warning("validation_error", title=opp.title[:60], error=str(e))

        logger.info("validation_complete", valid=len(validated), rejected=rejected)

        # ── Step 6: Dedup + Store ────────────────
        stored_count = 0
        try:
            stored_count = await self._store_opportunities(validated)
        except Exception as e:
            logger.error("store_failed", error=str(e))

        # ── Pipeline Summary ─────────────────────
        elapsed = (datetime.now(UTC) - start).total_seconds()

        summary = {
            "pipeline_id": pipeline_id,
            "topics": topics,
            "queries_generated": len(queries),
            "urls_found": len(unique_urls),
            "pages_crawled": len(crawled_pages),
            "opportunities_extracted": len(all_extracted),
            "opportunities_validated": len(validated),
            "opportunities_rejected": rejected,
            "opportunities_stored": stored_count,
            "elapsed_seconds": round(elapsed, 2),
        }

        logger.info("pipeline_complete", **summary)
        return summary

    async def _store_opportunities(self, opportunities: list[ExtractedOpportunity]) -> int:
        """Dedup and store validated opportunities in PostgreSQL."""
        from app.core.database import async_session_factory
        from app.services.opportunity_service import OpportunityService

        stored = 0
        stored_ids: list[str] = []

        async with async_session_factory() as db:
            service = OpportunityService(db)

            for opp in opportunities:
                # A source page can contain multiple distinct openings; dedup by listing identity.
                existing = await service.find_by_title_and_org(opp.title, opp.organization)
                if existing:
                    continue

                db_opp = await service.create_from_extraction(opp)
                stored_ids.append(str(db_opp.id))
                stored += 1

            await db.commit()

        if stored_ids:
            from app.workers.embedding_worker import embed_opportunity

            for opportunity_id in stored_ids:
                try:
                    embed_opportunity.delay(opportunity_id)
                except Exception as e:
                    logger.warning("embed_dispatch_failed", opp_id=opportunity_id, error=str(e))

        return stored

    async def close(self):
        """Clean up resources."""
        await self.search_agent.close()
        await self.crawler_agent.close()
