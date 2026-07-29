"""Search API — vector similarity search for opportunities."""

from typing import Any

from fastapi import APIRouter, Query

from app.agents.intelligence.embedding_agent import EmbeddingAgent
from app.vector.qdrant_service import QdrantService

router = APIRouter(prefix="/search", tags=["Search"])


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


@router.get("/similar/{opportunity_id}")
async def find_similar(
    opportunity_id: str,
    limit: int = Query(default=10, ge=1, le=50),
):
    """Find opportunities similar to a given one using vector similarity."""
    from qdrant_client import QdrantClient
    from app.config import get_settings

    settings = get_settings()
    client = QdrantClient(url=settings.qdrant_url)

    # Get the vector for the given opportunity
    try:
        points = client.retrieve(
            collection_name="opportunities",
            ids=[opportunity_id],
            with_vectors=True,
        )
    except Exception:
        return {"error": "Opportunity not found in vector store"}

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
