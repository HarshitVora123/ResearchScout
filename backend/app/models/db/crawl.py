"""SQLAlchemy ORM models for crawl sources and crawl history."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    Interval,
    Numeric,
    String,
    Text,
    Uuid,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class CrawlSource(Base):
    """A web source to crawl for research opportunities."""

    __tablename__ = "crawl_sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    domain: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    source_type: Mapped[str | None] = mapped_column(
        String(30)
    )  # university, company, government, lab, conference

    # ── Quality metrics ──────────────────────────
    trust_score: Mapped[float] = mapped_column(Numeric(3, 2), default=0.5)
    success_rate: Mapped[float] = mapped_column(Numeric(3, 2), default=1.0)
    total_crawls: Mapped[int] = mapped_column(Integer, default=0)
    total_opportunities_found: Mapped[int] = mapped_column(Integer, default=0)
    avg_confidence_score: Mapped[float] = mapped_column(Numeric(3, 2), default=0.5)

    # ── Crawl config ─────────────────────────────
    crawl_frequency_hours: Mapped[int] = mapped_column(Integer, default=168)  # 7 days
    last_crawled: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[int | None] = mapped_column(Integer)  # HTTP status code
    robots_txt: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_js: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[dict | None] = mapped_column(JSONB)  # Custom crawl config per source

    # ── Audit ────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<CrawlSource {self.domain!r}>"


class CrawlHistory(Base):
    """Record of individual crawl attempts."""

    __tablename__ = "crawl_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("crawl_sources.id")
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(Text)  # SHA-256 for change detection
    opportunities_found: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<CrawlHistory {self.url!r} status={self.status_code}>"
