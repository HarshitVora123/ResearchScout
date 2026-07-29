"""Neo4j knowledge graph service — schema, entity CRUD, and relationship management."""

import structlog
from neo4j import AsyncGraphDatabase, AsyncDriver

from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


async def get_neo4j_driver() -> AsyncDriver:
    """Create an async Neo4j driver."""
    return AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


# ── Schema Constraints (run once on startup) ────────
SCHEMA_QUERIES = [
    # Uniqueness constraints
    "CREATE CONSTRAINT IF NOT EXISTS FOR (o:Opportunity) REQUIRE o.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (org:Organization) REQUIRE org.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Researcher) REQUIRE r.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Country) REQUIRE c.name IS UNIQUE",
    # Indexes for fast lookup
    "CREATE INDEX IF NOT EXISTS FOR (o:Opportunity) ON (o.type)",
    "CREATE INDEX IF NOT EXISTS FOR (o:Opportunity) ON (o.is_active)",
    "CREATE INDEX IF NOT EXISTS FOR (org:Organization) ON (org.type)",
]


class Neo4jService:
    """
    High-level service for knowledge graph operations.

    Entity types:
    - Opportunity: research positions
    - Organization: universities, labs, companies
    - Researcher: professors, PIs
    - Topic: research areas
    - Skill: technical skills
    - Country: geographic locations

    Relationship types:
    - OFFERED_BY: Opportunity → Organization
    - SUPERVISED_BY: Opportunity → Researcher
    - REQUIRES_SKILL: Opportunity → Skill
    - COVERS_TOPIC: Opportunity → Topic
    - LOCATED_IN: Organization → Country
    - AFFILIATED_WITH: Researcher → Organization
    - RESEARCHES: Researcher → Topic
    - RELATED_TO: Topic ↔ Topic
    - SIMILAR_TO: Opportunity ↔ Opportunity
    """

    def __init__(self, driver: AsyncDriver | None = None):
        self._driver = driver
        self._owns_driver = driver is None

    async def _get_driver(self) -> AsyncDriver:
        if self._driver is None:
            self._driver = await get_neo4j_driver()
        return self._driver

    async def init_schema(self) -> None:
        """Create schema constraints and indexes."""
        driver = await self._get_driver()
        async with driver.session() as session:
            for query in SCHEMA_QUERIES:
                try:
                    await session.run(query)
                except Exception as e:
                    logger.warning("schema_query_failed", query=query[:60], error=str(e))
        logger.info("neo4j_schema_initialized")

    # ── Entity Creation ──────────────────────────────

    async def upsert_opportunity(
        self,
        opp_id: str,
        title: str,
        opp_type: str,
        is_active: bool = True,
        confidence: float = 0.5,
    ) -> None:
        """Create or update an Opportunity node."""
        driver = await self._get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MERGE (o:Opportunity {id: $id})
                SET o.title = $title,
                    o.type = $type,
                    o.is_active = $is_active,
                    o.confidence = $confidence,
                    o.updated_at = datetime()
                """,
                id=opp_id, title=title, type=opp_type,
                is_active=is_active, confidence=confidence,
            )

    async def upsert_organization(
        self, name: str, org_type: str = "university"
    ) -> None:
        """Create or update an Organization node."""
        driver = await self._get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MERGE (org:Organization {name: $name})
                SET org.type = $type, org.updated_at = datetime()
                """,
                name=name, type=org_type,
            )

    async def upsert_researcher(
        self, name: str, email: str | None = None
    ) -> None:
        """Create or update a Researcher node."""
        driver = await self._get_driver()
        async with driver.session() as session:
            query = "MERGE (r:Researcher {name: $name}) SET r.updated_at = datetime()"
            if email:
                query += ", r.email = $email"
            await session.run(query, name=name, email=email)

    async def upsert_topic(self, name: str) -> None:
        """Create or update a Topic node."""
        driver = await self._get_driver()
        async with driver.session() as session:
            await session.run(
                "MERGE (t:Topic {name: $name}) SET t.updated_at = datetime()",
                name=name,
            )

    async def upsert_skill(self, name: str) -> None:
        """Create or update a Skill node."""
        driver = await self._get_driver()
        async with driver.session() as session:
            await session.run(
                "MERGE (s:Skill {name: $name}) SET s.updated_at = datetime()",
                name=name,
            )

    async def upsert_country(self, name: str) -> None:
        """Create or update a Country node."""
        driver = await self._get_driver()
        async with driver.session() as session:
            await session.run(
                "MERGE (c:Country {name: $name}) SET c.updated_at = datetime()",
                name=name,
            )

    # ── Relationship Creation ────────────────────────

    async def link_opportunity_organization(
        self, opp_id: str, org_name: str
    ) -> None:
        """OFFERED_BY: Opportunity → Organization."""
        driver = await self._get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MATCH (o:Opportunity {id: $opp_id})
                MERGE (org:Organization {name: $org_name})
                MERGE (o)-[:OFFERED_BY]->(org)
                """,
                opp_id=opp_id, org_name=org_name,
            )

    async def link_opportunity_researcher(
        self, opp_id: str, researcher_name: str
    ) -> None:
        """SUPERVISED_BY: Opportunity → Researcher."""
        driver = await self._get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MATCH (o:Opportunity {id: $opp_id})
                MERGE (r:Researcher {name: $researcher_name})
                MERGE (o)-[:SUPERVISED_BY]->(r)
                """,
                opp_id=opp_id, researcher_name=researcher_name,
            )

    async def link_opportunity_topic(
        self, opp_id: str, topic_name: str
    ) -> None:
        """COVERS_TOPIC: Opportunity → Topic."""
        driver = await self._get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MATCH (o:Opportunity {id: $opp_id})
                MERGE (t:Topic {name: $topic_name})
                MERGE (o)-[:COVERS_TOPIC]->(t)
                """,
                opp_id=opp_id, topic_name=topic_name,
            )

    async def link_opportunity_skill(
        self, opp_id: str, skill_name: str
    ) -> None:
        """REQUIRES_SKILL: Opportunity → Skill."""
        driver = await self._get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MATCH (o:Opportunity {id: $opp_id})
                MERGE (s:Skill {name: $skill_name})
                MERGE (o)-[:REQUIRES_SKILL]->(s)
                """,
                opp_id=opp_id, skill_name=skill_name,
            )

    async def link_organization_country(
        self, org_name: str, country_name: str
    ) -> None:
        """LOCATED_IN: Organization → Country."""
        driver = await self._get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MERGE (org:Organization {name: $org_name})
                MERGE (c:Country {name: $country_name})
                MERGE (org)-[:LOCATED_IN]->(c)
                """,
                org_name=org_name, country_name=country_name,
            )

    async def link_researcher_organization(
        self, researcher_name: str, org_name: str
    ) -> None:
        """AFFILIATED_WITH: Researcher → Organization."""
        driver = await self._get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MERGE (r:Researcher {name: $researcher_name})
                MERGE (org:Organization {name: $org_name})
                MERGE (r)-[:AFFILIATED_WITH]->(org)
                """,
                researcher_name=researcher_name, org_name=org_name,
            )

    async def link_similar_opportunities(
        self, opp_id_a: str, opp_id_b: str, similarity: float
    ) -> None:
        """SIMILAR_TO: Opportunity ↔ Opportunity (bidirectional)."""
        driver = await self._get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MATCH (a:Opportunity {id: $id_a}), (b:Opportunity {id: $id_b})
                MERGE (a)-[r:SIMILAR_TO]-(b)
                SET r.similarity = $similarity
                """,
                id_a=opp_id_a, id_b=opp_id_b, similarity=similarity,
            )

    # ── Graph Queries ────────────────────────────────

    async def find_related_opportunities(
        self, opp_id: str, limit: int = 10
    ) -> list[dict]:
        """Find opportunities related via shared topics/skills/organizations."""
        driver = await self._get_driver()
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (o:Opportunity {id: $opp_id})-[:COVERS_TOPIC|REQUIRES_SKILL|OFFERED_BY]->(shared)
                      <-[:COVERS_TOPIC|REQUIRES_SKILL|OFFERED_BY]-(related:Opportunity)
                WHERE related.id <> $opp_id AND related.is_active = true
                WITH related, count(shared) AS shared_count
                ORDER BY shared_count DESC
                LIMIT $limit
                RETURN related.id AS id, related.title AS title,
                       related.type AS type, shared_count
                """,
                opp_id=opp_id, limit=limit,
            )
            return [dict(record) async for record in result]

    async def get_topic_cluster(
        self, topic_name: str, limit: int = 20
    ) -> list[dict]:
        """Get all active opportunities covering a topic."""
        driver = await self._get_driver()
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (t:Topic {name: $topic})<-[:COVERS_TOPIC]-(o:Opportunity)
                WHERE o.is_active = true
                RETURN o.id AS id, o.title AS title, o.type AS type, o.confidence AS confidence
                ORDER BY o.confidence DESC
                LIMIT $limit
                """,
                topic=topic_name, limit=limit,
            )
            return [dict(record) async for record in result]

    async def get_organization_profile(self, org_name: str) -> dict:
        """Get an organization's full profile from the graph."""
        driver = await self._get_driver()
        async with driver.session() as session:
            # Get opportunities
            opps = await session.run(
                """
                MATCH (org:Organization {name: $name})<-[:OFFERED_BY]-(o:Opportunity)
                RETURN count(o) AS total_opportunities,
                       count(CASE WHEN o.is_active THEN 1 END) AS active_opportunities,
                       collect(DISTINCT o.type) AS opportunity_types
                """,
                name=org_name,
            )
            opp_record = await opps.single()

            # Get researchers
            researchers = await session.run(
                """
                MATCH (org:Organization {name: $name})<-[:AFFILIATED_WITH]-(r:Researcher)
                RETURN collect(r.name) AS researchers
                """,
                name=org_name,
            )
            res_record = await researchers.single()

            # Get topics
            topics = await session.run(
                """
                MATCH (org:Organization {name: $name})<-[:OFFERED_BY]-(o:Opportunity)
                      -[:COVERS_TOPIC]->(t:Topic)
                RETURN collect(DISTINCT t.name) AS topics
                """,
                name=org_name,
            )
            topic_record = await topics.single()

            return {
                "name": org_name,
                "total_opportunities": opp_record["total_opportunities"] if opp_record else 0,
                "active_opportunities": opp_record["active_opportunities"] if opp_record else 0,
                "opportunity_types": opp_record["opportunity_types"] if opp_record else [],
                "researchers": res_record["researchers"] if res_record else [],
                "topics": topic_record["topics"] if topic_record else [],
            }

    async def graph_stats(self) -> dict:
        """Get basic graph statistics."""
        driver = await self._get_driver()
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (n)
                RETURN labels(n)[0] AS label, count(n) AS count
                ORDER BY count DESC
                """
            )
            node_counts = {record["label"]: record["count"] async for record in result}

            rel_result = await session.run(
                "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count ORDER BY count DESC"
            )
            rel_counts = {record["type"]: record["count"] async for record in rel_result}

            return {"nodes": node_counts, "relationships": rel_counts}

    async def close(self) -> None:
        """Close the driver if we own it."""
        if self._owns_driver and self._driver:
            await self._driver.close()
