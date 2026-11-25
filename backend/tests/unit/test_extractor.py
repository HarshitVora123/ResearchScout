"""Unit tests for the Extractor Agent."""

import json

from app.agents.intelligence.extractor_agent import ExtractorAgent


class TestExtractorParsing:
    """Test the JSON parsing logic of the Extractor Agent."""

    def setup_method(self):
        self.agent = ExtractorAgent()

    def test_parse_single_opportunity(self):
        """Test parsing a single opportunity from LLM JSON."""
        raw_json = json.dumps(
            [
                {
                    "title": "PhD Position in NLP",
                    "organization": "ETH Zurich",
                    "opportunity_type": "PhD",
                    "application_link": "https://ethz.ch/apply",
                    "country": "Switzerland",
                    "research_areas": ["NLP", "Machine Learning"],
                    "required_skills": ["Python", "PyTorch"],
                    "confidence_score": 0.9,
                }
            ]
        )

        results = self.agent._parse_results(raw_json, "https://ethz.ch/jobs")
        assert len(results) == 1
        assert results[0].title == "PhD Position in NLP"
        assert results[0].organization == "ETH Zurich"
        assert "NLP" in results[0].research_areas

    def test_parse_multiple_opportunities(self):
        """Test parsing multiple opportunities."""
        raw_json = json.dumps(
            [
                {
                    "title": "Research Intern",
                    "organization": "Google",
                    "application_link": "https://google.com/apply",
                },
                {
                    "title": "PhD Student",
                    "organization": "Stanford",
                    "application_link": "https://stanford.edu/apply",
                },
            ]
        )

        results = self.agent._parse_results(raw_json, "https://example.com")
        assert len(results) == 2

    def test_parse_wrapped_format(self):
        """Test parsing when LLM returns {opportunities: [...]}."""
        raw_json = json.dumps(
            {
                "opportunities": [
                    {
                        "title": "Fellowship",
                        "organization": "MIT",
                        "application_link": "https://mit.edu/apply",
                    }
                ]
            }
        )

        results = self.agent._parse_results(raw_json, "https://mit.edu")
        assert len(results) == 1
        assert results[0].title == "Fellowship"

    def test_parse_empty_list(self):
        """Test parsing empty results."""
        results = self.agent._parse_results("[]", "https://example.com")
        assert len(results) == 0

    def test_parse_invalid_json(self):
        """Test graceful handling of invalid JSON."""
        results = self.agent._parse_results("not valid json", "https://example.com")
        assert len(results) == 0

    def test_parse_partial_data(self):
        """Test parsing with partial/missing fields."""
        raw_json = json.dumps(
            [
                {
                    "title": "Some Position",
                    "organization": "Some Org",
                    "application_link": "https://example.com/apply",
                    # Minimal fields — many are optional
                }
            ]
        )

        results = self.agent._parse_results(raw_json, "https://example.com")
        assert len(results) == 1
        assert results[0].research_areas == []
        assert results[0].required_skills == []
        assert results[0].confidence_score == 0.5  # default
