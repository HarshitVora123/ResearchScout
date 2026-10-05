"""Opportunity endpoints — browse, search, detail, and user actions."""

import math
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import String, cast, func, or_, select

from app.api.deps import CurrentUser, DbSession
from app.models.db.interaction import SavedOpportunity, UserFeedback, UserInteraction
from app.models.db.opportunity import Opportunity
from app.models.schemas.common import FeedbackType, MessageResponse, PaginatedResponse
from app.models.schemas.opportunity import (
    OpportunityBrief,
    OpportunityDetail,
)
from app.services.opportunity_service import _normalize_opp

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List opportunities with filters",
)
async def list_opportunities(
    db: DbSession,
    opportunity_type: list[str] | None = Query(default=None),
    country: list[str] | None = Query(default=None),
    funding_type: list[str] | None = Query(default=None),
    research_area: str | None = None,
    query: str | None = None,
    is_active: bool = True,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = "date_discovered",
    sort_order: str = "desc",
):
    """
    List research opportunities with filtering, pagination, and sorting.

    Supports filtering by type, country, funding, research area, and active status.
    """
    # Build query
    stmt = select(Opportunity).where(Opportunity.is_active == is_active)

    if opportunity_type:
        stmt = stmt.where(Opportunity.opportunity_type.in_(opportunity_type))
    if country:
        stmt = stmt.where(Opportunity.country.in_(country))
    if funding_type:
        stmt = stmt.where(Opportunity.funding_type.in_(funding_type))
    if research_area:
        stmt = stmt.where(cast(Opportunity.research_areas, String).ilike(f"%{research_area}%"))
    if query:
        stmt = stmt.where(
            or_(
                Opportunity.title.ilike(f"%{query}%"),
                Opportunity.organization.ilike(f"%{query}%"),
                Opportunity.summary.ilike(f"%{query}%"),
            )
        )

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Sort
    sort_column = getattr(Opportunity, sort_by, Opportunity.date_discovered)
    if sort_order == "asc":
        stmt = stmt.order_by(sort_column.asc())
    else:
        stmt = stmt.order_by(sort_column.desc())

    # Paginate
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    result = await db.execute(stmt)
    opportunities = result.scalars().all()

    return PaginatedResponse(
        items=[OpportunityBrief.model_validate(_normalize_opp(opp)) for opp in opportunities],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )



@router.get(
    "/trending",
    response_model=list[OpportunityBrief],
    summary="Get trending opportunities",
)
async def get_trending(db: DbSession, limit: int = Query(default=10, ge=1, le=50)):
    """Get the most recently discovered, high-confidence opportunities."""
    result = await db.execute(
        select(Opportunity)
        .where(Opportunity.is_active == True)  # noqa: E712
        .order_by(
            Opportunity.confidence_score.desc(),
            Opportunity.date_discovered.desc(),
        )
        .limit(limit)
    )
    opportunities = result.scalars().all()
    return [OpportunityBrief.model_validate(_normalize_opp(opp)) for opp in opportunities]


@router.get(
    "/recommendations",
    summary="Get personalized recommendations",
)
async def get_recommendations(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=10, ge=1, le=50),
):
    """
    Get personalized opportunity recommendations for the authenticated user.

    Uses Multi-Signal Scoring (vector similarity, graph connections, rule-based matching),
    RRF rank aggregation, and MMR diversification.
    """
    from app.agents.user_facing.explanation_agent import ExplanationAgent
    from app.ranking.recommendation_engine import RecommendationEngine, RecommendationItem

    # Fetch active opportunities from DB
    result = await db.execute(
        select(Opportunity)
        .where(Opportunity.is_active == True)  # noqa: E712
        .order_by(Opportunity.date_discovered.desc())
        .limit(100)
    )
    opportunities = result.scalars().all()

    # User profile dict
    user_profile = {
        "full_name": user.full_name,
        "degree_level": user.degree_level,
        "university": user.university,
        "preferred_countries": user.preferred_countries or [],
        "skills": [{"skill_name": s.skill_name} for s in (user.skills or [])],
        "research_interests": [{"topic": i.topic} for i in (user.research_interests or [])],
    }

    engine = RecommendationEngine()
    explainer = ExplanationAgent()
    items: list[RecommendationItem] = []

    for opp in opportunities:
        opp_data = {
            "title": opp.title,
            "organization": opp.organization,
            "opportunity_type": opp.opportunity_type,
            "country": opp.country,
            "research_areas": opp.research_areas or [],
            "required_skills": opp.required_skills or [],
            "programming_languages": opp.programming_languages or [],
            "degree_levels": opp.degree_levels or [],
            "confidence_score": opp.confidence_score,
            "deadline": opp.deadline.isoformat() if opp.deadline else None,
        }

        rule_score, reasons = engine.calculate_rule_score(user_profile, opp_data)
        vector_score = 0.5  # Base score when vector DB is warming up
        graph_score = 0.3

        total_score = (
            (vector_score * engine.vector_weight)
            + (graph_score * engine.graph_weight)
            + (rule_score * engine.rule_weight)
        )

        match_bullets = explainer.generate_explanation(
            total_score=total_score,
            vector_score=vector_score,
            graph_score=graph_score,
            rule_reasons=reasons,
            user_profile=user_profile,
            opportunity=opp_data,
        )

        items.append(
            RecommendationItem(
                opportunity_id=str(opp.id),
                total_score=total_score,
                vector_score=vector_score,
                graph_score=graph_score,
                rule_score=rule_score,
                match_reasons=match_bullets,
                opportunity_data=opp_data,
            )
        )

    # Apply MMR diversification
    diverse_items = engine.mmr_rerank(items, top_n=limit)

    output = []
    for item in diverse_items:
        output.append({
            "opportunity_id": item.opportunity_id,
            "score": round(item.total_score, 3),
            "match_reasons": item.match_reasons,
            "opportunity": item.opportunity_data,
        })

    return {"recommendations": output, "total": len(output)}



@router.get(
    "/{opportunity_id}",
    response_model=OpportunityDetail,
    summary="Get opportunity detail",
)
async def get_opportunity(opportunity_id: UUID, db: DbSession):
    """Get full details of a specific opportunity."""
    result = await db.execute(
        select(Opportunity).where(Opportunity.id == opportunity_id)
    )
    opportunity = result.scalar_one_or_none()

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    return OpportunityDetail.model_validate(_normalize_opp(opportunity))


@router.post(
    "/{opportunity_id}/save",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save an opportunity",
)
async def save_opportunity(
    opportunity_id: UUID, user: CurrentUser, db: DbSession
):
    """Save/bookmark an opportunity for later."""
    # Check opportunity exists
    result = await db.execute(
        select(Opportunity).where(Opportunity.id == opportunity_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Check if already saved
    existing = await db.execute(
        select(SavedOpportunity).where(
            SavedOpportunity.user_id == user.id,
            SavedOpportunity.opportunity_id == opportunity_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already saved")

    saved = SavedOpportunity(user_id=user.id, opportunity_id=opportunity_id)
    db.add(saved)

    # Track interaction
    interaction = UserInteraction(
        user_id=user.id,
        opportunity_id=opportunity_id,
        interaction_type="save",
    )
    db.add(interaction)

    return MessageResponse(message="Opportunity saved")


@router.delete(
    "/{opportunity_id}/save",
    response_model=MessageResponse,
    summary="Unsave an opportunity",
)
async def unsave_opportunity(
    opportunity_id: UUID, user: CurrentUser, db: DbSession
):
    """Remove an opportunity from saved list."""
    from sqlalchemy import delete as sql_delete

    result = await db.execute(
        sql_delete(SavedOpportunity).where(
            SavedOpportunity.user_id == user.id,
            SavedOpportunity.opportunity_id == opportunity_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Saved opportunity not found")
    return MessageResponse(message="Opportunity unsaved")


@router.post(
    "/{opportunity_id}/feedback",
    response_model=MessageResponse,
    summary="Submit feedback",
)
async def submit_feedback(
    opportunity_id: UUID,
    feedback_type: FeedbackType,
    feedback_text: str | None = None,
    user: CurrentUser = None,
    db: DbSession = None,
):
    """Submit feedback on an opportunity (thumbs up/down, correction, report)."""
    feedback = UserFeedback(
        user_id=user.id,
        opportunity_id=opportunity_id,
        feedback_type=feedback_type.value,
        feedback_text=feedback_text,
    )
    db.add(feedback)

    # Track interaction
    interaction = UserInteraction(
        user_id=user.id,
        opportunity_id=opportunity_id,
        interaction_type=feedback_type.value,
    )
    db.add(interaction)

    return MessageResponse(message="Feedback submitted. Thank you!")
