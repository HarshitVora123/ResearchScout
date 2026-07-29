"""Pipeline admin endpoints — trigger discovery runs and manage crawl sources."""

import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession
from app.models.schemas.common import MessageResponse

router = APIRouter()


class DiscoveryRequest(BaseModel):
    """Request to trigger a discovery pipeline run."""

    topics: list[str] = Field(
        ..., min_length=1, max_length=10,
        description="Research topics to search for",
        examples=[["natural language processing", "reinforcement learning"]],
    )
    opportunity_types: list[str] | None = Field(
        default=None,
        description="Types of opportunities to search for",
        examples=[["PhD", "Internship", "Fellowship"]],
    )
    max_urls: int = Field(default=20, ge=1, le=100)
    search_engines: list[str] | None = Field(
        default=None,
        examples=[["google", "tavily"]],
    )


class DiscoverySummary(BaseModel):
    """Summary of a completed discovery run."""

    pipeline_id: str
    topics: list[str]
    queries_generated: int
    urls_found: int
    pages_crawled: int
    opportunities_extracted: int
    opportunities_validated: int
    opportunities_rejected: int
    opportunities_stored: int
    elapsed_seconds: float


class CrawlSourceCreate(BaseModel):
    """Request to add a new crawl source."""

    url: str
    domain: str
    source_type: str = "university"
    trust_score: float = Field(default=0.5, ge=0.0, le=1.0)
    crawl_frequency_hours: int = Field(default=168, ge=1)
    requires_js: bool = False


@router.post(
    "/discover",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a discovery pipeline run",
)
async def trigger_discovery(
    request: DiscoveryRequest,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
):
    """
    Trigger an asynchronous discovery pipeline run.

    The pipeline will:
    1. Generate search queries from topics
    2. Search across Google, Bing, Tavily
    3. Crawl discovered URLs
    4. Extract opportunities with LLM
    5. Validate and store results

    Results are stored in the database asynchronously.
    """
    # Import here to avoid circular imports
    from app.agents.orchestrator import DiscoveryPipeline

    async def run_pipeline():
        pipeline = DiscoveryPipeline()
        try:
            await pipeline.run(
                topics=request.topics,
                opportunity_types=request.opportunity_types,
                max_urls=request.max_urls,
                search_engines=request.search_engines,
            )
        finally:
            await pipeline.close()

    background_tasks.add_task(run_pipeline)

    return MessageResponse(
        message=f"Discovery pipeline started for topics: {', '.join(request.topics)}. "
        f"Results will appear in your feed shortly."
    )


@router.post(
    "/discover/sync",
    response_model=DiscoverySummary,
    summary="Run discovery pipeline synchronously (dev only)",
)
async def trigger_discovery_sync(
    request: DiscoveryRequest,
    user: CurrentUser,
):
    """
    Run the discovery pipeline synchronously and return results.

    Use for development/testing. For production, use the async endpoint.
    """
    from app.agents.orchestrator import DiscoveryPipeline

    pipeline = DiscoveryPipeline()
    try:
        result = await pipeline.run(
            topics=request.topics,
            opportunity_types=request.opportunity_types,
            max_urls=request.max_urls,
            search_engines=request.search_engines,
        )
        return DiscoverySummary(**result)
    finally:
        await pipeline.close()


@router.post(
    "/crawl/url",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue a single URL for crawling",
)
async def crawl_single_url(
    url: str,
    user: CurrentUser,
):
    """Queue a single URL for crawling via Celery."""
    from app.workers.crawl_worker import crawl_url

    crawl_url.delay(url=url)
    return MessageResponse(message=f"URL queued for crawling: {url}")


@router.post(
    "/sources/seed",
    response_model=MessageResponse,
    summary="Load seed sources from data/seed/sources.json",
)
async def seed_sources(db: DbSession, user: CurrentUser):
    """Load initial crawl sources from the seed file."""
    from app.services.opportunity_service import CrawlSourceService

    seed_path = Path(__file__).parents[4] / "data" / "seed" / "sources.json"
    if not seed_path.exists():
        raise HTTPException(status_code=404, detail="Seed file not found")

    with open(seed_path) as f:
        sources = json.load(f)

    service = CrawlSourceService(db)
    created = 0

    for source_data in sources:
        try:
            await service.create_source(
                url=source_data["url"],
                domain=source_data["domain"],
                source_type=source_data.get("source_type", "university"),
                trust_score=source_data.get("trust_score", 0.5),
                crawl_frequency_hours=source_data.get("crawl_frequency_hours", 168),
                requires_js=source_data.get("requires_js", False),
            )
            created += 1
        except Exception:
            # Skip duplicates
            continue

    return MessageResponse(message=f"Seeded {created} crawl sources")


@router.post(
    "/sources",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new crawl source",
)
async def add_crawl_source(
    request: CrawlSourceCreate,
    db: DbSession,
    user: CurrentUser,
):
    """Add a new URL to the crawl source registry."""
    from app.services.opportunity_service import CrawlSourceService

    service = CrawlSourceService(db)
    await service.create_source(
        url=request.url,
        domain=request.domain,
        source_type=request.source_type,
        trust_score=request.trust_score,
        crawl_frequency_hours=request.crawl_frequency_hours,
        requires_js=request.requires_js,
    )

    return MessageResponse(message=f"Crawl source added: {request.url}")


@router.post(
    "/crawl/scheduled",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger scheduled crawl of all due sources",
)
async def trigger_scheduled_crawl(user: CurrentUser):
    """Manually trigger the scheduled crawl (normally runs every 6 hours)."""
    from app.workers.crawl_worker import crawl_scheduled_sources

    crawl_scheduled_sources.delay()
    return MessageResponse(message="Scheduled crawl triggered")
