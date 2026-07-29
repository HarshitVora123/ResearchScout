"""Unit tests for Phase 4 — Notifier Agent and Application Assistant Agent."""

import pytest

from app.agents.user_facing.notifier_agent import NotifierAgent
from app.agents.user_facing.application_assistant import ApplicationAssistantAgent


class TestNotifierAgent:
    """Test notification formatting and dispatch."""

    @pytest.mark.asyncio
    async def test_send_email_mock(self):
        notifier = NotifierAgent()
        res = await notifier.send_email(
            to_email="user@example.com",
            subject="Test Subject",
            html_content="<p>Test</p>",
        )
        assert res is True

    @pytest.mark.asyncio
    async def test_send_telegram_mock(self):
        notifier = NotifierAgent()
        res = await notifier.send_telegram("12345", "Test message")
        assert res is True

    @pytest.mark.asyncio
    async def test_send_discord_mock(self):
        notifier = NotifierAgent()
        res = await notifier.send_discord(None, "Title", "Desc")
        assert res is True

    def test_daily_digest_html_formatting(self):
        notifier = NotifierAgent()
        recs = [
            {
                "match_reasons": ["Matching technical skills (100% overlap)"],
                "opportunity": {
                    "title": "PhD in NLP",
                    "organization": "Stanford University",
                    "country": "USA",
                },
            }
        ]
        html = notifier.generate_daily_digest_html("Jane", recs)
        assert "Stanford University" in html
        assert "Jane" in html
        assert "ResearchScout Daily Digest" in html


class TestApplicationAssistantAgent:
    """Test AI cover letter, email draft, reading list, and interview prep generators."""

    @pytest.mark.asyncio
    async def test_generate_cover_letter_fallback(self):
        assistant = ApplicationAssistantAgent()
        user_profile = {
            "full_name": "Jane Doe",
            "university": "MIT",
            "degree_level": "Master",
            "skills": ["Python", "PyTorch"],
        }
        opportunity = {
            "title": "PhD Position in NLP",
            "organization": "ETH Zurich",
            "professor": "Prof. Example",
            "research_areas": ["Natural Language Processing"],
        }

        letter = await assistant.generate_cover_letter(user_profile, opportunity)

        assert "Jane Doe" in letter
        assert "ETH Zurich" in letter
        assert "PhD Position in NLP" in letter
        assert "Python" in letter

    @pytest.mark.asyncio
    async def test_generate_email_draft(self):
        assistant = ApplicationAssistantAgent()
        user_profile = {
            "full_name": "Alex Smith",
            "degree_level": "M.S.",
        }
        opportunity = {
            "title": "Postdoc in AI",
            "organization": "Stanford AI Lab",
            "professor": "Prof. Andrew Ng",
            "research_areas": ["Deep Learning"],
        }

        draft = await assistant.generate_email_draft(user_profile, opportunity)

        assert "subject" in draft
        assert "body" in draft
        assert "Ng" in draft["body"]
        assert "Alex Smith" in draft["body"]

    @pytest.mark.asyncio
    async def test_generate_interview_prep(self):
        assistant = ApplicationAssistantAgent()
        opportunity = {
            "title": "AI Resident",
            "required_skills": ["PyTorch", "Transformers"],
            "research_areas": ["NLP"],
        }

        prep = await assistant.generate_interview_prep({}, opportunity)

        assert "technical_questions" in prep
        assert "questions_to_ask_pi" in prep
        assert len(prep["technical_questions"]) > 0

    @pytest.mark.asyncio
    async def test_generate_reading_list(self):
        assistant = ApplicationAssistantAgent()
        opportunity = {
            "organization": "MIT CSAIL",
            "research_areas": ["Computer Vision", "Robotics"],
        }

        readings = await assistant.generate_reading_list(opportunity)

        assert len(readings) == 2
        assert readings[0]["topic"] == "Computer Vision"
