"""Opportunity Service — database CRUD operations for research opportunities."""

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.crawl import CrawlHistory, CrawlSource
from app.models.db.opportunity import Opportunity
from app.models.schemas.opportunity import ExtractedOpportunity


def _normalize_opp(opp: Opportunity | None) -> Opportunity | None:
    """Helper to deserialize stringified JSON lists for SQLite compatibility."""
    if not opp:
        return None
    list_fields = [
        "research_areas", "keywords", "required_skills",
        "programming_languages", "degree_levels", "documents_required"
    ]
    for field in list_fields:
        val = getattr(opp, field, None)
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    setattr(opp, field, parsed)
            except Exception:
                setattr(opp, field, [])
    return opp


class OpportunityService:
    """Business logic for opportunity CRUD and search."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_from_extraction(
        self, extracted: ExtractedOpportunity
    ) -> Opportunity:
        """Create a new opportunity from an extracted record."""
        opp = Opportunity(
            id=uuid.uuid4(),
            title=extracted.title,
            opportunity_type=extracted.opportunity_type or "Other",
            organization=extracted.organization,
            department=extracted.department,
            research_lab=extracted.research_lab,
            professor=extracted.professor,
            professor_email=extracted.professor_email,
            country=extracted.country,
            city=extracted.city,
            location_type=extracted.location_type,
            research_areas=extracted.research_areas or [],
            keywords=extracted.keywords or [],
            required_skills=extracted.required_skills or [],
            programming_languages=extracted.programming_languages or [],
            required_gpa=extracted.required_gpa,
            eligibility_criteria={"criteria": extracted.eligibility_criteria}
            if extracted.eligibility_criteria else None,
            degree_levels=extracted.degree_levels or [],
            publications_required=extracted.publications_required,
            recommendation_letters=extracted.recommendation_letters,
            visa_requirements=extracted.visa_requirements,
            funding_type=extracted.funding_type,
            salary_range=extracted.salary_range,
            stipend=extracted.stipend,
            duration=extracted.duration,
            deadline=extracted.deadline,
            start_date=extracted.start_date,
            application_link=extracted.application_link,
            documents_required=extracted.documents_required or [],
            contact_email=extracted.contact_email,
            source_url=extracted.source_url,
            date_discovered=datetime.now(UTC),
            last_verified=datetime.now(UTC),
            confidence_score=extracted.confidence_score,
            authenticity_score=0.5,
            raw_text=extracted.raw_text[:10000] if extracted.raw_text else None,
            summary=extracted.summary,
            is_active=True,
            is_expired=False,
        )

        self.db.add(opp)
        await self.db.flush()
        return _normalize_opp(opp)  # type: ignore

    async def find_by_source_url(self, source_url: str) -> Opportunity | None:
        """Find an opportunity by its source URL (for dedup)."""
        result = await self.db.execute(
            select(Opportunity).where(Opportunity.source_url == source_url).limit(1)
        )
        return _normalize_opp(result.scalar_one_or_none())

    async def find_by_title_and_org(
        self, title: str, organization: str
    ) -> Opportunity | None:
        """Find an opportunity by title + org (for dedup)."""
        result = await self.db.execute(
            select(Opportunity).where(
                and_(
                    func.lower(Opportunity.title) == title.lower(),
                    func.lower(Opportunity.organization) == organization.lower(),
                )
            ).limit(1)
        )
        return _normalize_opp(result.scalar_one_or_none())

    async def get_by_id(self, opp_id: uuid.UUID) -> Opportunity | None:
        """Fetch a single opportunity by UUID."""
        result = await self.db.execute(
            select(Opportunity).where(Opportunity.id == opp_id)
        )
        return _normalize_opp(result.scalar_one_or_none())

    async def list_active(self, page: int = 1, page_size: int = 20) -> list[Opportunity]:
        """List active, non-expired opportunities."""
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(Opportunity)
            .where(
                Opportunity.is_active == True,
            )
            .order_by(Opportunity.date_discovered.desc())
            .offset(offset)
            .limit(page_size)
        )
        opps = result.scalars().all()
        return [_normalize_opp(o) for o in opps]  # type: ignore

    async def update_opportunity(
        self, opp_id: uuid.UUID, **kwargs
    ) -> None:
        """Update an existing opportunity."""
        await self.db.execute(
            update(Opportunity)
            .where(Opportunity.id == opp_id)
            .values(**kwargs, last_updated=datetime.now(UTC))
        )

    async def expire_past_deadlines(self) -> int:
        """Mark opportunities with past deadlines as expired."""
        result = await self.db.execute(
            update(Opportunity)
            .where(
                and_(
                    Opportunity.deadline < datetime.now(UTC),
                    Opportunity.is_expired == False,
                    Opportunity.deadline.isnot(None),
                )
            )
            .values(is_expired=True, is_active=False)
        )
        await self.db.commit()
        return result.rowcount

    async def count_active(self) -> int:
        """Count total active opportunities."""
        result = await self.db.execute(
            select(func.count()).where(
                Opportunity.is_active == True,
            )
        )
        return result.scalar() or 0
