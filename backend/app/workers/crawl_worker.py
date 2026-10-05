"""
Fully wired crawl worker — the complete crawl → clean → NLP → extract → validate → store pipeline.

Replaces the Week 1 stub with a production pipeline that:
1. Crawls a URL with rate limiting
2. Cleans HTML to markdown
3. Runs NLP pre-analysis (is this an opportunity page?)
4. Runs LLM structured extraction
5. Validates extracted data
6. Deduplicates against existing DB records
7. Stores new opportunities in PostgreSQL
8. Records crawl history
"""

import asyncio
import hashlib
import time
from datetime import UTC, datetime

import httpx
import structlog

from app.agents.tools.content_cleaner import (
    extract_meta_description,
    extract_page_title,
    html_to_markdown,
    truncate_for_llm,
)
from app.agents.tools.rate_limiter import InMemoryRateLimiter
from app.nlp.deadline_parser import parse_deadline
from app.nlp.keyword_extraction import analyze_text
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)

# Shared rate limiter across crawl tasks in this worker process
_rate_limiter = InMemoryRateLimiter()


@celery_app.task(
    name="app.workers.crawl_worker.crawl_url",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    queue="crawl",
)
def crawl_url(self, url: str, source_id: str | None = None, render_js: bool = False):
    """
    Crawl a single URL → clean → NLP check → extract → validate → store.

    The full pipeline runs synchronously inside Celery (each step feeds the next).
    """
    start = time.time()

    try:
        # ── Step 1: Rate Limiting ────────────────
        _rate_limiter.wait_and_acquire(url)

        # ── Step 2: Fetch the page ───────────────
        with httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "ResearchScoutBot/1.0 (+https://researchscout.io/bot)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        ) as client:
            response = client.get(url)

        duration_ms = int((time.time() - start) * 1000)
        raw_html = response.text
        content_hash = hashlib.sha256(raw_html.encode()).hexdigest()

        if response.status_code != 200:
            logger.warning(
                "crawl_failed",
                url=url,
                status=response.status_code,
                duration_ms=duration_ms,
            )
            return {
                "url": url,
                "status_code": response.status_code,
                "opportunities": 0,
                "duration_ms": duration_ms,
            }

        # ── Step 3: Clean content ────────────────
        title = extract_page_title(raw_html)
        _description = extract_meta_description(raw_html)  # kept for future use
        markdown = html_to_markdown(raw_html)

        if len(markdown.strip()) < 100:
            logger.info("page_too_short", url=url, length=len(markdown))
            return {
                "url": url,
                "status_code": 200,
                "opportunities": 0,
                "reason": "page_too_short",
                "duration_ms": duration_ms,
            }

        # ── Step 4: NLP Pre-analysis ─────────────
        nlp_result = analyze_text(markdown)

        if not nlp_result.is_opportunity:
            logger.info(
                "not_opportunity_page",
                url=url,
                title=title[:80],
            )
            return {
                "url": url,
                "status_code": 200,
                "opportunities": 0,
                "reason": "not_opportunity_page",
                "nlp_type_hint": nlp_result.opportunity_type_hint,
                "duration_ms": duration_ms,
            }

        # ── Step 5: Queue LLM extraction ─────────
        # Run extraction in the 'extract' queue so it doesn't
        # block the crawl workers
        extract_and_store.delay(
            url=url,
            title=title,
            markdown=truncate_for_llm(markdown),
            raw_text_snippet=markdown[:5000],
            nlp_skills=nlp_result.skills,
            nlp_languages=nlp_result.programming_languages,
            nlp_areas=nlp_result.research_areas,
            nlp_deadline=nlp_result.deadline_str,
            nlp_type_hint=nlp_result.opportunity_type_hint,
            content_hash=content_hash,
            source_id=source_id,
        )

        return {
            "url": url,
            "status_code": 200,
            "is_opportunity": True,
            "nlp_type_hint": nlp_result.opportunity_type_hint,
            "queued_extraction": True,
            "duration_ms": duration_ms,
        }

    except httpx.TimeoutException:
        logger.warning("crawl_timeout", url=url)
        raise self.retry(countdown=2**self.request.retries * 15)

    except httpx.ConnectError:
        logger.warning("crawl_connect_error", url=url)
        raise self.retry(countdown=2**self.request.retries * 20)

    except Exception as exc:
        logger.error("crawl_error", url=url, error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries * 10)


@celery_app.task(
    name="app.workers.crawl_worker.extract_and_store",
    bind=True,
    max_retries=2,
    queue="extract",
)
def extract_and_store(
    self,
    url: str,
    title: str,
    markdown: str,
    raw_text_snippet: str,
    nlp_skills: list[str],
    nlp_languages: list[str],
    nlp_areas: list[str],
    nlp_deadline: str | None,
    nlp_type_hint: str | None,
    content_hash: str,
    source_id: str | None = None,
):
    """
    Run LLM extraction → validation → dedup → store.

    Runs in the 'extract' queue, separate from crawl workers.
    Uses asyncio.run() to bridge Celery's sync workers with async agents.
    """
    try:
        result = asyncio.run(
            _async_extract_and_store(
                url=url,
                title=title,
                markdown=markdown,
                raw_text_snippet=raw_text_snippet,
                nlp_skills=nlp_skills,
                nlp_languages=nlp_languages,
                nlp_areas=nlp_areas,
                nlp_deadline=nlp_deadline,
                nlp_type_hint=nlp_type_hint,
                content_hash=content_hash,
                source_id=source_id,
            )
        )
        return result
    except Exception as exc:
        logger.error("extraction_error", url=url, error=str(exc))
        raise self.retry(exc=exc, countdown=30)


async def _async_extract_and_store(
    url: str,
    title: str,
    markdown: str,
    raw_text_snippet: str,
    nlp_skills: list[str],
    nlp_languages: list[str],
    nlp_areas: list[str],
    nlp_deadline: str | None,
    nlp_type_hint: str | None,
    content_hash: str,
    source_id: str | None,
) -> dict:
    """Async inner function for extract_and_store."""
    from app.agents.intelligence.extractor_agent import ExtractorAgent
    from app.agents.intelligence.validator_agent import ValidatorAgent
    from app.core.database import async_session_factory
    from app.services.opportunity_service import OpportunityService

    extractor = ExtractorAgent()
    validator = ValidatorAgent()

    # ── Step 1: LLM Extraction ───────────────────
    extracted_list = await extractor.extract(
        content=markdown,
        url=url,
        title=title,
    )

    if not extracted_list:
        logger.info("no_opportunities_extracted", url=url)
        return {"url": url, "opportunities_found": 0}

    # ── Step 2: Enrich with NLP data ─────────────
    for opp in extracted_list:
        # Merge NLP-extracted data (if LLM missed them)
        if not opp.required_skills:
            opp.required_skills = nlp_skills
        if not opp.programming_languages:
            opp.programming_languages = nlp_languages
        if not opp.research_areas:
            opp.research_areas = nlp_areas
        if not opp.opportunity_type and nlp_type_hint:
            opp.opportunity_type = nlp_type_hint
        if not opp.deadline and nlp_deadline:
            opp.deadline = parse_deadline(nlp_deadline)

        # Store raw text snippet for validation
        opp.raw_text = raw_text_snippet

    # ── Step 3: Validate each opportunity ────────
    stored_count = 0

    async with async_session_factory() as db:
        service = OpportunityService(db)

        for opp in extracted_list:
            # Validate
            report = await validator.validate(opp)

            if not report.is_valid:
                logger.info(
                    "opportunity_rejected",
                    url=url,
                    title=opp.title[:80],
                    issues=report.issues,
                )
                continue

            # Update confidence with validation score
            opp.confidence_score = min(
                opp.confidence_score,
                report.authenticity_score,
            )

            # ── Step 4: Dedup ────────────────────
            existing = await service.find_by_source_url(opp.source_url)
            if existing:
                logger.debug("duplicate_source_url", url=opp.source_url)
                continue

            existing = await service.find_by_title_and_org(
                opp.title, opp.organization
            )
            if existing:
                logger.debug(
                    "duplicate_title_org",
                    title=opp.title[:80],
                    org=opp.organization,
                )
                continue

            # ── Step 5: Store ────────────────────
            db_opp = await service.create_from_extraction(opp)
            stored_count += 1

            logger.info(
                "opportunity_stored",
                id=str(db_opp.id),
                title=opp.title[:80],
                org=opp.organization,
                type=opp.opportunity_type,
                confidence=opp.confidence_score,
            )

            # ── Step 6: Queue embedding + KG ingestion ──
            try:
                from app.workers.embedding_worker import embed_opportunity
                embed_opportunity.delay(str(db_opp.id))
            except Exception as e:
                logger.warning("embed_dispatch_failed", opp_id=str(db_opp.id), error=str(e))

        await db.commit()

    return {
        "url": url,
        "opportunities_found": len(extracted_list),
        "opportunities_stored": stored_count,
        "opportunities_rejected": len(extracted_list) - stored_count,
    }


@celery_app.task(
    name="app.workers.crawl_worker.crawl_scheduled_sources",
    queue="crawl",
)
def crawl_scheduled_sources():
    """
    Crawl all sources that are due for a refresh.

    Called periodically by Celery Beat (every 6 hours).
    """
    result = asyncio.run(_async_crawl_scheduled())
    return result


async def _async_crawl_scheduled() -> dict:
    """Async inner for scheduled crawling."""
    from app.core.database import async_session_factory
    from app.services.opportunity_service import CrawlSourceService

    async with async_session_factory() as db:
        service = CrawlSourceService(db)
        due_sources = await service.get_due_sources(limit=50)

    dispatched = 0
    for source in due_sources:
        crawl_url.delay(
            url=source.url,
            source_id=str(source.id),
            render_js=source.requires_js,
        )
        dispatched += 1

    logger.info("scheduled_crawl_dispatched", count=dispatched)
    return {
        "status": "dispatched",
        "sources_dispatched": dispatched,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@celery_app.task(
    name="app.workers.crawl_worker.expire_old_opportunities",
    queue="default",
)
def expire_old_opportunities():
    """Mark opportunities with past deadlines as expired."""
    result = asyncio.run(_async_expire())
    return result


async def _async_expire() -> dict:
    """Async inner for expiration."""
    from app.core.database import async_session_factory
    from app.services.opportunity_service import OpportunityService

    async with async_session_factory() as db:
        service = OpportunityService(db)
        count = await service.expire_past_deadlines()

    logger.info("expired_opportunities", count=count)
    return {
        "status": "complete",
        "expired_count": count,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@celery_app.task(
    name="app.workers.crawl_worker.batch_crawl_urls",
    queue="crawl",
)
def batch_crawl_urls(urls: list[str], source_id: str | None = None):
    """Dispatch individual crawl_url tasks for a batch of URLs."""
    for url in urls:
        crawl_url.delay(url=url, source_id=source_id)
    return {"dispatched": len(urls)}
