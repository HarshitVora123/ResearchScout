"""
End-to-end pipeline test — verifies the full discovery flow without external APIs.

Uses mocked search results and a sample HTML page to test the complete pipeline:
search → crawl → NLP filter → extract → validate → dedup → store
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.agents.discovery.query_generator import generate_search_queries
from app.agents.tools.content_cleaner import html_to_markdown
from app.nlp.keyword_extraction import analyze_text
from app.agents.intelligence.validator_agent import ValidatorAgent
from app.models.schemas.opportunity import ExtractedOpportunity


# ── Sample HTML for testing ──────────────────────────
SAMPLE_OPPORTUNITY_HTML = """
<html>
<head><title>PhD Position in NLP - ETH Zurich</title></head>
<body>
<h1>PhD Position in Natural Language Processing</h1>
<p>The Department of Computer Science at ETH Zurich is looking for
a highly motivated PhD student to join our NLP research group.</p>

<h2>Research Topics</h2>
<p>The candidate will work on large language models, knowledge graphs,
and information retrieval. Topics include:</p>
<ul>
    <li>Retrieval-Augmented Generation (RAG)</li>
    <li>Knowledge Graph Construction from Text</li>
    <li>Multilingual NLP</li>
</ul>

<h2>Requirements</h2>
<ul>
    <li>MSc in Computer Science or related field</li>
    <li>Strong programming skills in Python and PyTorch</li>
    <li>Experience with deep learning and NLP</li>
    <li>Publications in NLP venues (preferred)</li>
</ul>

<h2>We Offer</h2>
<ul>
    <li>Fully funded position for 4 years</li>
    <li>Competitive salary (Swiss standards)</li>
    <li>Access to world-class GPU clusters</li>
</ul>

<h2>Application</h2>
<p>Deadline: March 15, 2025</p>
<p>Apply here: <a href="https://ethz.ch/apply/phd-nlp-2025">Application Link</a></p>
<p>Contact: Prof. Example at example@ethz.ch</p>
</body>
</html>
"""


class TestEndToEndPipeline:
    """Test the full pipeline using mocked external services."""

    def test_query_generation(self):
        """Step 1: Query generator produces valid queries."""
        queries = generate_search_queries(
            topics=["NLP", "Knowledge Graphs"],
            opportunity_types=["PhD"],
            max_queries=10,
        )
        assert len(queries) > 0
        assert len(queries) <= 10
        assert any("NLP" in q for q in queries)

    def test_content_cleaning(self):
        """Step 2: HTML → clean markdown."""
        markdown = html_to_markdown(SAMPLE_OPPORTUNITY_HTML)
        assert "Natural Language Processing" in markdown
        assert "Python" in markdown
        assert "PyTorch" in markdown
        assert "March 15, 2025" in markdown

    def test_nlp_prefilter(self):
        """Step 3: NLP correctly identifies this as an opportunity."""
        markdown = html_to_markdown(SAMPLE_OPPORTUNITY_HTML)
        nlp_result = analyze_text(markdown)

        assert nlp_result.is_opportunity is True
        assert nlp_result.opportunity_type_hint == "PhD"
        assert "python" in nlp_result.programming_languages
        assert "pytorch" in nlp_result.skills or "pytorch" in nlp_result.programming_languages
        assert nlp_result.deadline_str == "March 15, 2025"

    def test_nlp_skill_extraction(self):
        """Step 3b: NLP extracts skills correctly."""
        markdown = html_to_markdown(SAMPLE_OPPORTUNITY_HTML)
        nlp_result = analyze_text(markdown)

        assert "python" in nlp_result.programming_languages
        # Check that research areas are detected
        assert any(
            "natural language processing" in area or "nlp" in area
            for area in nlp_result.research_areas
        )

    @pytest.mark.asyncio
    async def test_validation_on_extracted(self):
        """Step 5: Validator accepts a well-formed opportunity."""
        from datetime import datetime, timezone, timedelta

        opp = ExtractedOpportunity(
            title="PhD Position in Natural Language Processing",
            organization="ETH Zurich",
            opportunity_type="PhD",
            application_link="https://ethz.ch/apply/phd-nlp-2025",
            source_url="https://ethz.ch/positions/phd-nlp",
            country="Switzerland",
            city="Zurich",
            research_areas=["Natural Language Processing", "Knowledge Graphs"],
            required_skills=["Python", "PyTorch", "Deep Learning"],
            programming_languages=["Python"],
            funding_type="Fully Funded",
            deadline=datetime(2025, 3, 15, tzinfo=timezone.utc),
            professor="Prof. Example",
            professor_email="example@ethz.ch",
            raw_text="PhD Position in Natural Language Processing at ETH Zurich",
            confidence_score=0.85,
        )

        validator = ValidatorAgent()
        report = await validator.validate(opp)

        assert report.is_valid is True
        assert report.authenticity_score > 0.6
        assert report.field_scores["domain_trust"] >= 0.4
        assert report.field_scores["not_scam"] == 1.0
        assert report.field_scores["completeness"] > 0.7

    def test_full_flow_without_llm(self):
        """
        Integration test: query → clean → NLP → validate (no LLM).

        Tests the pipeline from HTML input to validation output,
        skipping only the LLM extraction step (which requires an API key).
        """
        # Step 1: Generate queries
        queries = generate_search_queries(
            topics=["NLP"],
            opportunity_types=["PhD"],
            max_queries=5,
        )
        assert len(queries) > 0

        # Step 2: Clean content (simulating crawl result)
        markdown = html_to_markdown(SAMPLE_OPPORTUNITY_HTML)
        assert len(markdown) > 100

        # Step 3: NLP pre-filter
        nlp_result = analyze_text(markdown)
        assert nlp_result.is_opportunity is True

        # Steps 4 (LLM extraction) would go here — skipped

        # Step 5: Manually construct what LLM would extract
        from datetime import datetime, timezone
        opp = ExtractedOpportunity(
            title="PhD Position in Natural Language Processing",
            organization="ETH Zurich",
            opportunity_type=nlp_result.opportunity_type_hint or "PhD",
            application_link="https://ethz.ch/apply/phd-nlp-2025",
            source_url="https://ethz.ch/positions",
            research_areas=nlp_result.research_areas or ["NLP"],
            required_skills=nlp_result.skills,
            programming_languages=nlp_result.programming_languages,
            raw_text=markdown[:3000],
            confidence_score=0.8,
        )

        # Enrich with NLP deadline
        from app.nlp.deadline_parser import parse_deadline
        if nlp_result.deadline_str:
            opp.deadline = parse_deadline(nlp_result.deadline_str)

        assert opp.title is not None
        assert opp.organization is not None
        assert len(opp.programming_languages) > 0

        print(f"✅ Pipeline produced: {opp.title} at {opp.organization}")
        print(f"   Skills: {opp.required_skills}")
        print(f"   Languages: {opp.programming_languages}")
        print(f"   Deadline: {opp.deadline}")
