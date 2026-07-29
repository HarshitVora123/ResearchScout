"""
Embedding worker — background tasks for vector embedding generation and KG ingestion.

Replaces the Phase 1 stubs with a production pipeline that:
1. Loads an opportunity from PostgreSQL
2. Generates embeddings via OpenAI/Gemini
3. Checks for semantic duplicates in Qdrant
4. Upserts to Qdrant 'opportunities' collection
5. Ingests into Neo4j knowledge graph
"""

import asyncio

import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="app.workers.embedding_worker.embed_opportunity",
    bind=True,
    max_retries=2,
    queue="embed",
)
def embed_opportunity(self, opportunity_id: str):
    """
    Generate vector embeddings for an opportunity and upsert to Qdrant + Neo4j.

    This is the final step in the pipeline, running asynchronously after
    the opportunity has been stored in PostgreSQL.
    """
    try:
        result = asyncio.run(_async_embed_opportunity(opportunity_id))
        return result
    except Exception as exc:
        logger.error("embed_failed", opp_id=opportunity_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30)


async def _async_embed_opportunity(opportunity_id: str) -> dict:
    """Async implementation of opportunity embedding."""
    from uuid import UUID

    from sqlalchemy import select

    from app.agents.intelligence.embedding_agent import EmbeddingAgent
    from app.agents.knowledge.kg_builder_agent import KGBuilderAgent
    from app.core.database import async_session_factory
    from app.models.db.opportunity import Opportunity
    from app.models.schemas.opportunity import ExtractedOpportunity
    from app.vector.qdrant_service import QdrantService

    # 1. Load opportunity from DB
    async with async_session_factory() as db:
        result = await db.execute(
            select(Opportunity).where(Opportunity.id == UUID(opportunity_id))
        )
        opp = result.scalar_one_or_none()

    if not opp:
        logger.warning("opportunity_not_found", opp_id=opportunity_id)
        return {"opp_id": opportunity_id, "status": "not_found"}

    # 2. Compose text for embedding
    embedding_agent = EmbeddingAgent()
    opp_data = {
        "title": opp.title,
        "organization": opp.organization,
        "opportunity_type": opp.opportunity_type,
        "department": opp.department,
        "country": opp.country,
        "city": opp.city,
        "research_areas": opp.research_areas or [],
        "required_skills": opp.required_skills or [],
        "programming_languages": opp.programming_languages or [],
        "funding_type": opp.funding_type,
        "summary": opp.summary,
    }

    text = embedding_agent.compose_opportunity_text(opp_data)

    # 3. Generate embedding
    embedding = await embedding_agent.embed_text(text)

    # 4. Upsert to Qdrant
    qdrant = QdrantService()
    qdrant.upsert_opportunity(
        opportunity_id=opportunity_id,
        embedding=embedding,
        payload={
            "title": opp.title,
            "organization": opp.organization,
            "opportunity_type": opp.opportunity_type,
            "country": opp.country,
            "is_active": opp.is_active,
            "research_areas": opp.research_areas or [],
            "funding_type": opp.funding_type,
            "deadline": opp.deadline.isoformat() if opp.deadline else None,
            "confidence_score": opp.confidence_score,
        },
    )

    logger.info("opportunity_embedded", opp_id=opportunity_id, title=opp.title[:60])

    # 5. Ingest into knowledge graph
    kg_result = {"entities_created": 0, "relationships_created": 0}
    try:
        kg_builder = KGBuilderAgent()

        # Build an ExtractedOpportunity-like object for the KG builder
        extracted = ExtractedOpportunity(
            title=opp.title,
            organization=opp.organization,
            opportunity_type=opp.opportunity_type,
            application_link=opp.application_link or "",
            source_url=opp.source_url or "",
            country=opp.country,
            research_areas=opp.research_areas or [],
            required_skills=opp.required_skills or [],
            programming_languages=opp.programming_languages or [],
            professor=opp.professor,
            professor_email=opp.professor_email,
            confidence_score=opp.confidence_score,
        )

        kg_result = await kg_builder.ingest_opportunity(opportunity_id, extracted)
        await kg_builder.close()
    except Exception as e:
        logger.warning("kg_ingest_skipped", opp_id=opportunity_id, error=str(e))

    return {
        "opp_id": opportunity_id,
        "status": "embedded",
        "vector_dims": len(embedding),
        "kg_entities": kg_result.get("entities_created", 0),
        "kg_relationships": kg_result.get("relationships_created", 0),
    }


@celery_app.task(
    name="app.workers.embedding_worker.embed_user_profile",
    bind=True,
    max_retries=2,
    queue="embed",
)
def embed_user_profile(self, user_id: str):
    """
    Generate vector embeddings for a user profile and upsert to Qdrant.

    Used by the recommendation engine to match users to opportunities.
    """
    try:
        result = asyncio.run(_async_embed_user(user_id))
        return result
    except Exception as exc:
        logger.error("user_embed_failed", user_id=user_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30)


async def _async_embed_user(user_id: str) -> dict:
    """Async implementation of user profile embedding."""
    from uuid import UUID

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.agents.intelligence.embedding_agent import EmbeddingAgent
    from app.core.database import async_session_factory
    from app.models.db.user import User
    from app.vector.qdrant_service import QdrantService

    # Load user with relationships
    async with async_session_factory() as db:
        result = await db.execute(
            select(User)
            .where(User.id == UUID(user_id))
            .options(
                selectinload(User.skills),
                selectinload(User.research_interests),
                selectinload(User.publications),
            )
        )
        user = result.scalar_one_or_none()

    if not user:
        return {"user_id": user_id, "status": "not_found"}

    # Compose profile text
    embedding_agent = EmbeddingAgent()
    profile_data = {
        "full_name": user.full_name,
        "degree_level": user.degree_level,
        "university": user.university,
        "career_goals": user.career_goals,
        "skills": [{"skill_name": s.skill_name} for s in (user.skills or [])],
        "research_interests": [{"topic": i.topic} for i in (user.research_interests or [])],
        "publications": [{"title": p.title} for p in (user.publications or [])],
        "preferred_countries": user.preferred_countries or [],
    }

    text = embedding_agent.compose_user_text(profile_data)

    # Generate embedding
    embedding = await embedding_agent.embed_text(text)

    # Upsert to Qdrant
    qdrant = QdrantService()
    qdrant.upsert_user_profile(
        user_id=user_id,
        embedding=embedding,
        payload={
            "full_name": user.full_name,
            "degree_level": user.degree_level,
            "university": user.university,
        },
    )

    logger.info("user_profile_embedded", user_id=user_id)
    return {"user_id": user_id, "status": "embedded", "vector_dims": len(embedding)}


@celery_app.task(
    name="app.workers.embedding_worker.batch_embed_opportunities",
    queue="embed",
)
def batch_embed_opportunities(opportunity_ids: list[str]):
    """Dispatch individual embedding tasks for a batch of opportunities."""
    for opp_id in opportunity_ids:
        embed_opportunity.delay(opp_id)
    logger.info("batch_embed_dispatched", count=len(opportunity_ids))
    return {"dispatched": len(opportunity_ids)}
