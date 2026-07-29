"""Shared agent state definitions for LangGraph orchestration."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.schemas.agent import AgentTask, CrawlResult, SearchResult, TaskStatus
from app.models.schemas.opportunity import ExtractedOpportunity


class PipelineState(BaseModel):
    """
    Shared state for the discovery pipeline.

    This state flows through the LangGraph graph:
    Planner → Search → Crawl → Extract → Validate → Dedup → Store

    Each agent reads from and writes to this shared state.
    """

    # ── Pipeline metadata ────────────────────────
    pipeline_id: str = ""
    goal: str = ""
    status: TaskStatus = TaskStatus.PENDING
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    # ── Planner outputs ──────────────────────────
    tasks: list[AgentTask] = []
    search_queries: list[dict[str, Any]] = []

    # ── Search outputs ───────────────────────────
    search_results: list[SearchResult] = []
    urls_to_crawl: list[str] = []

    # ── Crawler outputs ──────────────────────────
    crawl_results: list[CrawlResult] = []

    # ── Extractor outputs ────────────────────────
    extracted_opportunities: list[ExtractedOpportunity] = []

    # ── Validator outputs ────────────────────────
    validated_opportunities: list[ExtractedOpportunity] = []

    # ── Dedup outputs ────────────────────────────
    unique_opportunities: list[ExtractedOpportunity] = []
    duplicate_count: int = 0

    # ── Counters and metrics ─────────────────────
    urls_searched: int = 0
    urls_crawled: int = 0
    opportunities_extracted: int = 0
    opportunities_stored: int = 0
    errors: list[str] = []

    # ── Control flow ─────────────────────────────
    current_agent: str = ""
    should_continue: bool = True
    max_urls: int = 50
