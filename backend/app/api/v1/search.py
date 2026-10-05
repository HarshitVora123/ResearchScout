"""Search API — text search and vector similarity search for opportunities."""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.sql import func

from app.api.deps import DbSession
from app.models.db.opportunity import Opportunity

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/")
async def text_search(
    db: DbSession,
    q: str = Query(..., description="Search query"),
    limit: int = Query(default=20, ge=1, le=100),
    page: int = Query(default=1, ge=1),
):
    """
    Basic text search for research opportunities.

    Searches across title, organization, summary, research_areas, and keywords.
    """
    search_term = f"%{q}%"
    offset = (page - 1) * limit

    # Search across multiple fields
    query = (
        select(Opportunity)
        .where(
            Opportunity.is_active == True,  # noqa: E712
            or_(
                Opportunity.title.ilike(search_term),
                Opportunity.organization.ilike(search_term),
                Opportunity.summary.ilike(search_term),
                Opportunity.country.ilike(search_term),
                Opportunity.opportunity_type.ilike(search_term),
                Opportunity.department.ilike(search_term),
                Opportunity.professor.ilike(search_term),
            ),
        )
        .order_by(Opportunity.date_discovered.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    opportunities = result.scalars().all()

    # Count total
    count_query = (
        select(func.count())
        .select_from(Opportunity)
        .where(
            Opportunity.is_active == True,  # noqa: E712
            or_(
                Opportunity.title.ilike(search_term),
                Opportunity.organization.ilike(search_term),
                Opportunity.summary.ilike(search_term),
                Opportunity.country.ilike(search_term),
                Opportunity.opportunity_type.ilike(search_term),
            ),
        )
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return {
        "query": q,
        "results": [
            {
                "id": str(opp.id),
                "title": opp.title,
                "opportunity_type": opp.opportunity_type,
                "organization": opp.organization,
                "country": opp.country,
                "city": opp.city,
                "summary": opp.summary,
                "research_areas": opp.research_areas or [],
                "deadline": str(opp.deadline) if opp.deadline else None,
                "confidence_score": opp.confidence_score,
            }
            for opp in opportunities
        ],
        "total": total,
        "page": page,
        "page_size": limit,
    }


@router.get("/semantic")
async def semantic_search(
    q: str = Query(..., description="Natural language search query"),
    limit: int = Query(default=20, ge=1, le=100),
    opportunity_type: list[str] | None = Query(default=None),
    country: str | None = Query(default=None),
):
    """
    Semantic search for research opportunities.

    Converts the query to a vector embedding and searches Qdrant
    for the most similar opportunities.
    """
    try:
        from app.agents.intelligence.embedding_agent import EmbeddingAgent
        from app.vector.qdrant_service import QdrantService

        # Generate query embedding
        embedding_agent = EmbeddingAgent()
        query_vector = await embedding_agent.embed_text(q)

        # Build filters
        filters = {}
        if opportunity_type:
            filters["opportunity_type"] = opportunity_type
        if country:
            filters["country"] = country
        filters["is_active"] = True

        # Search Qdrant
        qdrant = QdrantService()
        results = qdrant.search_similar_opportunities(
            query_vector=query_vector,
            limit=limit,
            score_threshold=0.35,
            filters=filters if len(filters) > 1 else {"is_active": True},
        )

        return {
            "query": q,
            "results": results,
            "total": len(results),
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Semantic search is currently unavailable. The vector search service (Qdrant) or embedding API is not accessible. Error: {type(e).__name__}: {str(e)[:200]}. Use the basic text search endpoint (/api/v1/search/?q=...) instead.",
        )


@router.get("/similar/{opportunity_id}")
async def find_similar(
    opportunity_id: str,
    limit: int = Query(default=10, ge=1, le=50),
):
    """Find opportunities similar to a given one using vector similarity."""
    try:
        from qdrant_client import QdrantClient

        from app.config import get_settings
        from app.vector.qdrant_service import QdrantService

        settings = get_settings()
        client = QdrantClient(url=settings.qdrant_url, timeout=2)

        # Get the vector for the given opportunity
        points = client.retrieve(
            collection_name="opportunities",
            ids=[opportunity_id],
            with_vectors=True,
        )

        if not points:
            return {"error": "Opportunity not found in vector store"}

        query_vector = points[0].vector

        qdrant = QdrantService()
        results = qdrant.search_similar_opportunities(
            query_vector=query_vector,
            limit=limit + 1,  # +1 to exclude self
            score_threshold=0.5,
        )

        # Filter out the query opportunity itself
        results = [r for r in results if r["id"] != opportunity_id][:limit]

        return {
            "opportunity_id": opportunity_id,
            "similar": results,
            "total": len(results),
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Similar search unavailable. Qdrant vector store is not running. Error: {type(e).__name__}: {str(e)[:200]}",
        )
