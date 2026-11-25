"""SQLAlchemy ORM model for research opportunities."""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Opportunity(Base):
    """A research opportunity extracted from the web."""

    __tablename__ = "opportunities"

    # ── Identity ─────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    opportunity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # PhD, Internship, Fellowship, Scholarship, etc.

    # ── Organization ─────────────────────────────
    organization: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    department: Mapped[str | None] = mapped_column(Text)
    research_lab: Mapped[str | None] = mapped_column(Text)
    professor: Mapped[str | None] = mapped_column(Text)
    professor_email: Mapped[str | None] = mapped_column(Text)

    # ── Location ─────────────────────────────────
    country: Mapped[str | None] = mapped_column(String(100), index=True)
    city: Mapped[str | None] = mapped_column(String(100))
    location_type: Mapped[str | None] = mapped_column(String(20))  # Remote / Hybrid / Onsite

    # ── Research ─────────────────────────────────
    research_areas: Mapped[list[str] | None] = mapped_column(JSON)
    keywords: Mapped[list[str] | None] = mapped_column(JSON)
    required_skills: Mapped[list[str] | None] = mapped_column(JSON)
    programming_languages: Mapped[list[str] | None] = mapped_column(JSON)

    # ── Eligibility ──────────────────────────────
    required_gpa: Mapped[float | None] = mapped_column(Numeric(3, 2))
    eligibility_criteria: Mapped[dict | None] = mapped_column(JSON)
    degree_levels: Mapped[list[str] | None] = mapped_column(JSON)
    publications_required: Mapped[bool] = mapped_column(Boolean, default=False)
    recommendation_letters: Mapped[int | None] = mapped_column(Integer)
    visa_requirements: Mapped[str | None] = mapped_column(Text)

    # ── Compensation & Funding ───────────────────
    funding_type: Mapped[str | None] = mapped_column(
        String(30)
    )  # Fully Funded / Partially Funded / Unfunded
    salary_range: Mapped[str | None] = mapped_column(String(100))
    stipend: Mapped[str | None] = mapped_column(String(100))

    # ── Dates & Application ──────────────────────
    duration: Mapped[str | None] = mapped_column(String(50))
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    application_link: Mapped[str] = mapped_column(Text, nullable=False)
    documents_required: Mapped[list[str] | None] = mapped_column(JSON)
    contact_email: Mapped[str | None] = mapped_column(Text)

    # ── Source & Verification ────────────────────
    source_url: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    date_discovered: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    last_verified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_updated: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    confidence_score: Mapped[float] = mapped_column(Numeric(3, 2), default=0.5)
    authenticity_score: Mapped[float] = mapped_column(Numeric(3, 2), default=0.5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_text: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)

    # Vector store reference
    qdrant_point_id: Mapped[str | None] = mapped_column(String(64))

    # ── Timestamps ───────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Opportunity {self.title!r} @ {self.organization!r}>"


# Additional Indexes for Search Performance
Index("ix_opportunities_type_country", Opportunity.opportunity_type, Opportunity.country)
