"""Unit tests for the Validator Agent."""

from datetime import UTC, datetime, timedelta

import pytest

from app.agents.intelligence.validator_agent import ValidatorAgent
from app.models.schemas.opportunity import ExtractedOpportunity


@pytest.fixture
def validator():
    return ValidatorAgent()


def make_opportunity(**kwargs) -> ExtractedOpportunity:
    """Helper to create test opportunities with defaults."""
    defaults = {
        "title": "PhD Position in Machine Learning",
        "organization": "MIT",
        "application_link": "https://mit.edu/apply",
        "source_url": "https://mit.edu/positions/phd-ml",
        "opportunity_type": "PhD",
        "country": "USA",
        "research_areas": ["Machine Learning"],
        "deadline": datetime.now(UTC) + timedelta(days=30),
        "confidence_score": 0.8,
        "raw_text": "PhD Position in Machine Learning at MIT. Apply by 2025.",
    }
    defaults.update(kwargs)
    return ExtractedOpportunity(**defaults)


class TestValidatorAgent:
    """Test the Validator Agent's checks."""

    @pytest.mark.asyncio
    async def test_valid_opportunity_passes(self, validator):
        opp = make_opportunity()
        report = await validator.validate(opp)
        assert report.is_valid is True
        assert report.authenticity_score > 0.5

    @pytest.mark.asyncio
    async def test_trusted_edu_domain(self, validator):
        opp = make_opportunity(source_url="https://cs.stanford.edu/positions")
        report = await validator.validate(opp)
        assert report.field_scores["domain_trust"] >= 0.9

    @pytest.mark.asyncio
    async def test_trusted_known_domain(self, validator):
        opp = make_opportunity(source_url="https://openai.com/careers")
        report = await validator.validate(opp)
        assert report.field_scores["domain_trust"] == 1.0

    @pytest.mark.asyncio
    async def test_unknown_domain_lower_trust(self, validator):
        opp = make_opportunity(source_url="https://random-unknown-site.xyz/jobs")
        report = await validator.validate(opp)
        assert report.field_scores["domain_trust"] < 0.5

    @pytest.mark.asyncio
    async def test_past_deadline_flagged(self, validator):
        opp = make_opportunity(deadline=datetime(2020, 1, 1, tzinfo=UTC))
        report = await validator.validate(opp)
        assert report.field_scores["temporal_ok"] < 0.5
        assert any("past" in issue.lower() for issue in report.issues)

    @pytest.mark.asyncio
    async def test_no_deadline_neutral(self, validator):
        opp = make_opportunity(deadline=None)
        report = await validator.validate(opp)
        assert report.field_scores["temporal_ok"] == 0.5

    @pytest.mark.asyncio
    async def test_invalid_url_flagged(self, validator):
        opp = make_opportunity(application_link="not-a-url")
        report = await validator.validate(opp)
        assert report.field_scores["url_valid"] < 0.5

    @pytest.mark.asyncio
    async def test_scam_detected(self, validator):
        opp = make_opportunity(
            raw_text="Pay a fee of $500 to register. Send money via Western Union."
        )
        report = await validator.validate(opp)
        assert report.field_scores["not_scam"] < 0.5
        assert report.is_valid is False

    @pytest.mark.asyncio
    async def test_missing_critical_fields(self, validator):
        opp = make_opportunity(
            title="",
            organization="",
        )
        report = await validator.validate(opp)
        assert report.field_scores["completeness"] < 0.6

    @pytest.mark.asyncio
    async def test_text_consistency_good(self, validator):
        opp = make_opportunity(
            title="PhD in NLP at MIT",
            organization="MIT",
            raw_text="PhD in NLP at MIT. Apply now for this position.",
        )
        report = await validator.validate(opp)
        assert report.field_scores["text_consistent"] > 0.5

    @pytest.mark.asyncio
    async def test_text_consistency_bad(self, validator):
        """Hallucination detection: title doesn't match source text."""
        opp = make_opportunity(
            title="Deep Learning Research at Google Brain",
            organization="Google",
            raw_text="Welcome to the MIT cooking club page. Join us for recipes.",
        )
        report = await validator.validate(opp)
        assert report.field_scores["text_consistent"] < 0.5
