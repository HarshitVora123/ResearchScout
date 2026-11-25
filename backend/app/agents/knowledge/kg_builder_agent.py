"""
KG Builder Agent — extracts entities and relationships from opportunities
and populates the Neo4j knowledge graph.

This agent runs after extraction + validation and enriches the KG with:
- Organization nodes (linked to country)
- Researcher nodes (linked to organization)
- Topic nodes (linked to opportunity)
- Skill nodes (linked to opportunity)
- Inter-opportunity similarity edges
"""

import structlog

from app.knowledge_graph.neo4j_service import Neo4jService
from app.models.schemas.opportunity import ExtractedOpportunity

logger = structlog.get_logger(__name__)


class KGBuilderAgent:
    """
    Populates the knowledge graph from extracted opportunity data.

    Called after an opportunity is validated and stored in PostgreSQL.
    Creates nodes and relationships in Neo4j.
    """

    def __init__(self, neo4j_service: Neo4jService | None = None):
        self.neo4j = neo4j_service or Neo4jService()

    async def ingest_opportunity(
        self,
        opp_id: str,
        opp: ExtractedOpportunity,
    ) -> dict:
        """
        Ingest a single opportunity into the knowledge graph.

        Creates:
        - Opportunity node
        - Organization node + OFFERED_BY edge
        - Topic nodes + COVERS_TOPIC edges
        - Skill nodes + REQUIRES_SKILL edges
        - Researcher node + SUPERVISED_BY edge (if professor is known)
        - Country node + LOCATED_IN edge (if country is known)
        """
        entities_created = 0
        relationships_created = 0

        try:
            # 1. Opportunity node
            await self.neo4j.upsert_opportunity(
                opp_id=opp_id,
                title=opp.title,
                opp_type=opp.opportunity_type or "Other",
                is_active=True,
                confidence=opp.confidence_score,
            )
            entities_created += 1

            # 2. Organization
            if opp.organization:
                org_type = _infer_org_type(opp.organization)
                await self.neo4j.upsert_organization(opp.organization, org_type)
                await self.neo4j.link_opportunity_organization(opp_id, opp.organization)
                entities_created += 1
                relationships_created += 1

                # Link org to country
                if opp.country:
                    await self.neo4j.upsert_country(opp.country)
                    await self.neo4j.link_organization_country(opp.organization, opp.country)
                    entities_created += 1
                    relationships_created += 1

            # 3. Topics (research areas)
            for area in opp.research_areas or []:
                normalized = area.strip().title()
                if len(normalized) > 2:
                    await self.neo4j.upsert_topic(normalized)
                    await self.neo4j.link_opportunity_topic(opp_id, normalized)
                    entities_created += 1
                    relationships_created += 1

            # 4. Skills
            for skill in (opp.required_skills or [])[:10]:
                normalized = skill.strip().lower()
                if len(normalized) > 1:
                    await self.neo4j.upsert_skill(normalized)
                    await self.neo4j.link_opportunity_skill(opp_id, normalized)
                    entities_created += 1
                    relationships_created += 1

            # 5. Programming languages (as skills)
            for lang in opp.programming_languages or []:
                normalized = lang.strip().lower()
                if normalized:
                    await self.neo4j.upsert_skill(normalized)
                    await self.neo4j.link_opportunity_skill(opp_id, normalized)
                    entities_created += 1
                    relationships_created += 1

            # 6. Researcher (professor/supervisor)
            if opp.professor:
                await self.neo4j.upsert_researcher(
                    opp.professor,
                    email=opp.professor_email,
                )
                await self.neo4j.link_opportunity_researcher(opp_id, opp.professor)
                entities_created += 1
                relationships_created += 1

                # Link researcher to organization
                if opp.organization:
                    await self.neo4j.link_researcher_organization(opp.professor, opp.organization)
                    relationships_created += 1

            logger.info(
                "kg_ingested",
                opp_id=opp_id,
                title=opp.title[:60],
                entities=entities_created,
                relationships=relationships_created,
            )

        except Exception as e:
            logger.error(
                "kg_ingest_failed",
                opp_id=opp_id,
                error=str(e),
            )

        return {
            "opp_id": opp_id,
            "entities_created": entities_created,
            "relationships_created": relationships_created,
        }

    async def close(self) -> None:
        """Clean up resources."""
        await self.neo4j.close()


def _infer_org_type(org_name: str) -> str:
    """Infer organization type from name."""
    name_lower = org_name.lower()

    university_keywords = [
        "university",
        "universität",
        "université",
        "universidad",
        "institute of technology",
        "polytechnic",
        "college",
        "school of",
        "department of",
        "eth ",
        "epfl",
        "mit",
        "lab ",
        "laboratory",
    ]
    company_keywords = [
        "google",
        "microsoft",
        "meta",
        "amazon",
        "apple",
        "nvidia",
        "openai",
        "anthropic",
        "deepmind",
        "hugging face",
        "stability",
    ]
    government_keywords = [
        "nsf",
        "nih",
        "darpa",
        "ministry",
        "national",
        "european",
        "council",
    ]

    if any(kw in name_lower for kw in university_keywords):
        return "university"
    if any(kw in name_lower for kw in company_keywords):
        return "company"
    if any(kw in name_lower for kw in government_keywords):
        return "government"

    return "research_institute"
