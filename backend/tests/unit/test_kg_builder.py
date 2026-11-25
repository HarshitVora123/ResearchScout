"""Unit tests for the KG Builder Agent — entity extraction and relationship creation."""

from unittest.mock import AsyncMock

import pytest

from app.agents.knowledge.kg_builder_agent import KGBuilderAgent, _infer_org_type
from app.models.schemas.opportunity import ExtractedOpportunity


class TestInferOrgType:
    """Test organization type inference."""

    def test_university(self):
        assert _infer_org_type("Massachusetts Institute of Technology") == "university"
        assert _infer_org_type("Stanford University") == "university"
        assert _infer_org_type("ETH Zurich - Department of Computer Science") == "university"

    def test_company(self):
        assert _infer_org_type("Google") == "company"
        assert _infer_org_type("OpenAI") == "company"
        assert _infer_org_type("Microsoft Research") == "company"
        assert _infer_org_type("DeepMind") == "company"

    def test_government(self):
        assert _infer_org_type("National Science Foundation") == "government"
        assert _infer_org_type("European Research Council") == "government"

    def test_unknown(self):
        assert _infer_org_type("SomeRandomOrg") == "research_institute"


class TestKGBuilderAgent:
    """Test KG ingestion logic."""

    @pytest.mark.asyncio
    async def test_ingest_creates_entities(self):
        """Verify that ingest calls the right Neo4j methods."""
        mock_neo4j = AsyncMock()

        agent = KGBuilderAgent(neo4j_service=mock_neo4j)

        opp = ExtractedOpportunity(
            title="PhD in NLP",
            organization="MIT",
            opportunity_type="PhD",
            application_link="https://mit.edu/apply",
            source_url="https://mit.edu/positions/phd",
            country="USA",
            research_areas=["NLP", "Machine Learning"],
            required_skills=["Python", "PyTorch"],
            programming_languages=["Python"],
            professor="Prof. Example",
            professor_email="example@mit.edu",
            confidence_score=0.8,
        )

        result = await agent.ingest_opportunity("opp-123", opp)

        # Verify entities were created
        assert result["entities_created"] > 0
        assert result["relationships_created"] > 0

        # Verify specific method calls
        mock_neo4j.upsert_opportunity.assert_called_once()
        mock_neo4j.upsert_organization.assert_called_once()
        mock_neo4j.link_opportunity_organization.assert_called_once()
        mock_neo4j.upsert_country.assert_called_once()
        mock_neo4j.link_organization_country.assert_called_once()
        mock_neo4j.upsert_researcher.assert_called_once()
        mock_neo4j.link_opportunity_researcher.assert_called_once()

        # Verify topics were created (NLP + Machine Learning)
        assert mock_neo4j.upsert_topic.call_count == 2
        assert mock_neo4j.link_opportunity_topic.call_count == 2

    @pytest.mark.asyncio
    async def test_ingest_minimal_opportunity(self):
        """Test ingestion with minimal data (no professor, country, etc.)."""
        mock_neo4j = AsyncMock()
        agent = KGBuilderAgent(neo4j_service=mock_neo4j)

        opp = ExtractedOpportunity(
            title="Research Position",
            organization="SomeOrg",
            application_link="https://example.com",
            source_url="https://example.com",
            confidence_score=0.5,
        )

        await agent.ingest_opportunity("opp-456", opp)

        # Should still create opportunity + organization
        mock_neo4j.upsert_opportunity.assert_called_once()
        mock_neo4j.upsert_organization.assert_called_once()

        # Should NOT create researcher or country
        mock_neo4j.upsert_researcher.assert_not_called()
        mock_neo4j.upsert_country.assert_not_called()

    @pytest.mark.asyncio
    async def test_ingest_handles_errors_gracefully(self):
        """Test that Neo4j errors don't crash the agent."""
        mock_neo4j = AsyncMock()
        mock_neo4j.upsert_opportunity.side_effect = Exception("Neo4j down")

        agent = KGBuilderAgent(neo4j_service=mock_neo4j)

        opp = ExtractedOpportunity(
            title="Test",
            organization="TestOrg",
            application_link="https://example.com",
            source_url="https://example.com",
            confidence_score=0.5,
        )

        # Should not raise — errors are caught internally
        result = await agent.ingest_opportunity("opp-err", opp)
        assert result["opp_id"] == "opp-err"
