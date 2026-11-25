"""Tests for resume parsing, recommendations, explanations, and feedback."""

import pytest

from app.agents.user_facing.explanation_agent import ExplanationAgent
from app.nlp.resume_parser import ResumeParser
from app.ranking.feedback_loop import FeedbackAgent
from app.ranking.recommendation_engine import RecommendationEngine


class TestResumeParser:
    """Test resume parsing logic."""

    def test_parse_contact_and_education(self):
        parser = ResumeParser()
        sample_resume = """
        Dr. Alex Rivera
        alex.rivera@stanford.edu | (555) 123-4567

        Education
        Stanford University - Master of Science in Computer Science
        GPA: 3.95/4.00

        Skills & Languages
        Python, PyTorch, C++, Natural Language Processing, Machine Learning, Transformers

        Publications
        1. "Advances in Retrieval-Augmented Generation", NeurIPS 2024
        """

        parsed = parser.parse_text(sample_resume)

        assert parsed.full_name == "Dr. Alex Rivera"
        assert parsed.email == "alex.rivera@stanford.edu"
        assert parsed.degree_level == "Master"
        assert parsed.gpa == 3.95
        assert "stanford" in (parsed.university or "").lower()
        assert "python" in [s.lower() for s in parsed.programming_languages + parsed.skills]
        assert len(parsed.publications) > 0

    def test_groups_project_titles_and_descriptions_and_normalizes_indian_cgpa(self):
        resume = """Education
Pune Institute of Computer Technology CGPA: 9.60
BE – Artificial Intelligence & Data Science Aug 2023 – Jun 2027
Projects
Home-Accessible Brain Tumour Screening and Triage Ongoing
Research Advisor: Faculty Name
– Investigated brain tumour detection approaches and available datasets, including
methods to identify feasibility constraints and gaps in accessible screening.
– Formulated a home-accessible screening and triage research direction.
3D Endoscopic Reconstruction Pipeline
– Developed a 3D reconstruction pipeline using Python and OpenCV.
– Implemented point cloud generation on endoscopy datasets.
Technical Skills
Python, OpenCV
"""

        parsed = ResumeParser().parse_text(resume)

        assert parsed.university == "Pune Institute of Computer Technology"
        assert parsed.gpa == pytest.approx(3.84)
        assert parsed.degree_level == "Bachelor"
        assert parsed.major == "Artificial Intelligence & Data Science"
        assert [project["title"] for project in parsed.projects] == [
            "Home-Accessible Brain Tumour Screening and Triage",
            "3D Endoscopic Reconstruction Pipeline",
        ]
        assert "methods to identify feasibility constraints" in parsed.projects[0]["description"]
        assert "Formulated a home-accessible" in parsed.projects[0]["description"]
        assert {"python", "opencv"}.issubset(set(parsed.projects[1]["technologies"]))


class TestRecommendationEngine:
    """Test multi-signal recommendation scoring and MMR reranking."""

    def test_rule_score_calculation(self):
        engine = RecommendationEngine()

        user_profile = {
            "full_name": "Jane Doe",
            "degree_level": "Master",
            "preferred_countries": ["Switzerland", "Germany"],
            "skills": [{"skill_name": "Python"}, {"skill_name": "PyTorch"}],
            "research_interests": [{"topic": "Natural Language Processing"}],
        }

        opp_matching = {
            "title": "PhD Position in NLP",
            "opportunity_type": "PhD",
            "country": "Switzerland",
            "required_skills": ["Python", "PyTorch"],
            "programming_languages": ["Python"],
            "research_areas": ["Natural Language Processing"],
            "degree_levels": ["Master"],
        }

        score, reasons = engine.calculate_rule_score(user_profile, opp_matching)

        assert score > 0.6
        assert len(reasons) >= 3
        assert any("Switzerland" in r for r in reasons)
        assert any("skills" in r.lower() for r in reasons)

    def test_mmr_diversification(self):
        engine = RecommendationEngine()

        from app.ranking.recommendation_engine import RecommendationItem

        item1 = RecommendationItem(
            opportunity_id="1",
            total_score=0.9,
            vector_score=0.9,
            graph_score=0.8,
            rule_score=0.9,
            match_reasons=["Reason 1"],
            opportunity_data={"organization": "ETH Zurich", "research_areas": ["NLP"]},
        )
        item2 = RecommendationItem(
            opportunity_id="2",
            total_score=0.88,
            vector_score=0.88,
            graph_score=0.8,
            rule_score=0.85,
            match_reasons=["Reason 2"],
            opportunity_data={"organization": "ETH Zurich", "research_areas": ["NLP"]},
        )
        item3 = RecommendationItem(
            opportunity_id="3",
            total_score=0.85,
            vector_score=0.85,
            graph_score=0.7,
            rule_score=0.8,
            match_reasons=["Reason 3"],
            opportunity_data={"organization": "Stanford", "research_areas": ["Computer Vision"]},
        )

        reranked = engine.mmr_rerank([item1, item2, item3], lambda_param=0.5, top_n=3)

        assert len(reranked) == 3
        assert reranked[0].opportunity_id == "1"
        # Stanford item should be boosted for diversity over near-identical ETH item
        assert reranked[1].opportunity_id == "3"


class TestExplanationAgent:
    """Test match explanation generation."""

    def test_generate_explanation_bullets(self):
        explainer = ExplanationAgent()

        bullets = explainer.generate_explanation(
            total_score=0.92,
            vector_score=0.9,
            graph_score=0.8,
            rule_reasons=[
                "Located in target country (Switzerland)",
                "Matching technical skills (100% overlap)",
            ],
            user_profile={"full_name": "Test User"},
            opportunity={"confidence_score": 0.95, "deadline": "2025-05-01"},
        )

        assert len(bullets) >= 4
        assert any("92%" in b for b in bullets)
        assert any("Switzerland" in b for b in bullets)


class TestFeedbackAgent:
    """Test dynamic feedback processing."""

    def test_process_save_interaction(self):
        agent = FeedbackAgent()

        opp_data = {
            "title": "PhD Position in NLP",
            "research_areas": ["Natural Language Processing"],
            "required_skills": ["Python", "PyTorch"],
            "country": "Germany",
        }

        update = agent.process_interaction("save", opp_data)

        assert update.topic_delta.get("Natural Language Processing") == 1.0
        assert update.skill_delta.get("python") == 1.0
        assert update.country_delta.get("Germany") == 1.0
