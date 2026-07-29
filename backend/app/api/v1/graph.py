"""Knowledge Graph API — explore the research graph."""

from fastapi import APIRouter, Query

from app.knowledge_graph.neo4j_service import Neo4jService

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])


@router.get("/stats")
async def graph_stats():
    """Get knowledge graph statistics (node/relationship counts)."""
    service = Neo4jService()
    try:
        stats = await service.graph_stats()
        return stats
    finally:
        await service.close()


@router.get("/related/{opportunity_id}")
async def get_related_opportunities(
    opportunity_id: str,
    limit: int = Query(default=10, ge=1, le=50),
):
    """
    Find opportunities related to a given one via shared
    topics, skills, and organizations in the knowledge graph.
    """
    service = Neo4jService()
    try:
        related = await service.find_related_opportunities(opportunity_id, limit)
        return {"opportunity_id": opportunity_id, "related": related}
    finally:
        await service.close()


@router.get("/topic/{topic_name}")
async def get_topic_cluster(
    topic_name: str,
    limit: int = Query(default=20, ge=1, le=100),
):
    """Get all active opportunities covering a specific research topic."""
    service = Neo4jService()
    try:
        opportunities = await service.get_topic_cluster(topic_name, limit)
        return {"topic": topic_name, "opportunities": opportunities}
    finally:
        await service.close()


@router.get("/organization/{org_name}")
async def get_organization_profile(org_name: str):
    """
    Get an organization's full profile from the knowledge graph:
    opportunity counts, types, researchers, and topics.
    """
    service = Neo4jService()
    try:
        profile = await service.get_organization_profile(org_name)
        return profile
    finally:
        await service.close()
