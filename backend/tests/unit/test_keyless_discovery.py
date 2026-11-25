"""Regression tests for discovery without optional API credentials."""

from app.agents.intelligence.extractor_agent import ExtractorAgent


def test_rule_extractor_returns_explicit_opportunity_without_llm():
    content = """# PhD Position in Cross-Lingual Information Retrieval

We are looking for a doctoral student to join the research group.
The position is fully funded. Apply by 30 November 2026.
Applicants should have experience with Python and information retrieval.
"""

    opportunities = ExtractorAgent._extract_rule_based(
        content,
        "https://cs.example.edu/openings/phd-ir",
        "PhD Position in Cross-Lingual Information Retrieval",
    )

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.title == "PhD Position in Cross-Lingual Information Retrieval"
    assert opportunity.opportunity_type == "PhD"
    assert opportunity.application_link.endswith("phd-ir")
    assert opportunity.organization == "cs.example.edu"
    assert "python" in opportunity.programming_languages
    assert opportunity.confidence_score < 0.7


def test_rule_extractor_rejects_pages_without_explicit_opening():
    content = """# Cross-Lingual Information Retrieval

This paper studies ranking methods and evaluates a benchmark dataset.
The results include Python code and a new dataset for future research.
"""

    assert not ExtractorAgent._extract_rule_based(
        content, "https://example.edu/paper", "Cross-Lingual Information Retrieval"
    )
