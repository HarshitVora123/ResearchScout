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
import urllib.robotparser
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx
import structlog

from app.agents.tools.content_cleaner import (
    extract_meta_description,
    extract_page_title,
    html_to_markdown,
    truncate_for_llm,
)
from app.agents.tools.rate_limiter import RedisSyncRateLimiter
from app.config import get_settings
from app.nlp.deadline_parser import parse_deadline
from app.nlp.keyword_extraction import analyze_text
from app.core.url_safety import resolve_redirect, validate_public_http_url
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)

# Shared rate limiter across crawl tasks in this worker process
_rate_limiter = RedisSyncRateLimiter(get_settings().redis_url)


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
        current_url = validate_public_http_url(url)
        with httpx.Client(
            timeout=30.0,
            follow_redirects=False,
            headers={
                "User-Agent": "ResearchScoutBot/1.0 (+https://researchscout.io/bot)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        ) as client:
            for _ in range(6):
                parsed_url = urlparse(current_url)
                robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
                robots_response = client.get(robots_url)
                if robots_response.status_code != 404:
                    if robots_response.status_code != 200:
                        raise PermissionError("Unable to verify robots.txt access policy")
                    robots = urllib.robotparser.RobotFileParser()
                    robots.set_url(robots_url)
                    robots.parse(robots_response.text.splitlines())
                    if not robots.can_fetch("ResearchScoutBot/1.0", current_url):
                        raise PermissionError("Crawl disallowed by robots.txt")
                with client.stream("GET", current_url) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if location:
                            current_url = resolve_redirect(current_url, location)
                            continue
                    size_header = response.headers.get("content-length")
                    if size_header and int(size_header) > 5 * 1024 * 1024:
                        raise ValueError("Page exceeds the 5 MiB crawl limit")
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > 5 * 1024 * 1024:
                            raise ValueError("Page exceeds the 5 MiB crawl limit")
                    raw_html = bytes(body).decode(response.encoding or "utf-8", errors="replace")
                    response_status = response.status_code
            else:
                raise ValueError("Too many redirects")

        duration_ms = int((time.time() - start) * 1000)
        content_hash = hashlib.sha256(raw_html.encode()).hexdigest()

        asyncio.run(_record_crawl_result(
            source_id, url, response_status, content_hash, duration_ms,
            None if response_status == 200 else f"HTTP {response_status}",
        ))

        if response_status != 200:
            logger.warning(
                "crawl_failed",
                url=url,
                status=response_status,
                duration_ms=duration_ms,
            )
            return {
                "url": url,
                "status_code": response_status,
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


async def _record_crawl_result(
    source_id: str | None,
    url: str,
    status_code: int,
    content_hash: str,
    duration_ms: int,
    error_message: str | None,
) -> None:
    """Persist crawl history and update the source's health counters."""
    from uuid import UUID

    from app.core.database import async_session_factory
    from app.models.db.crawl import CrawlHistory, CrawlSource
    from sqlalchemy import select

    parsed_source_id = None
    if source_id:
        try:
            parsed_source_id = UUID(source_id)
        except ValueError:
            parsed_source_id = None
    async with async_session_factory() as db:
        db.add(CrawlHistory(
            source_id=parsed_source_id,
            url=url,
            status_code=status_code,
            content_hash=content_hash,
            duration_ms=duration_ms,
            error_message=error_message,
        ))
        if parsed_source_id:
            result = await db.execute(select(CrawlSource).where(CrawlSource.id == parsed_source_id))
            source = result.scalar_one_or_none()
            if source:
                previous_count = source.total_crawls
                previous_rate = float(source.success_rate)
                source.total_crawls = previous_count + 1
                source.last_crawled = datetime.now(UTC)
                source.last_status = status_code
                source.success_rate = (previous_rate * previous_count + (1 if status_code == 200 else 0)) / (previous_count + 1)
        await db.commit()


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
        dispatched_at = datetime.now(UTC)
        for source in due_sources:
            source.last_crawled = dispatched_at
        await db.commit()

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
