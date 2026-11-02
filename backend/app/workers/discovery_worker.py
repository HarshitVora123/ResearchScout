"""Durable Celery task for user-triggered discovery runs."""

import asyncio

from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.discovery_worker.run_discovery", queue="default")
def run_discovery(
    topics: list[str],
    opportunity_types: list[str] | None = None,
    max_urls: int = 20,
    search_engines: list[str] | None = None,
) -> dict:
    from app.agents.orchestrator import DiscoveryPipeline

    async def run() -> dict:
        pipeline = DiscoveryPipeline()
        try:
            return await pipeline.run(topics, opportunity_types, max_urls, search_engines)
        finally:
            await pipeline.close()

    return asyncio.run(run())
