"""Unit tests for the NLP pipeline — keyword extraction, deadline parsing, skill extraction."""

from datetime import UTC, datetime

import pytest

from app.nlp.deadline_parser import days_until_deadline, is_deadline_valid, parse_deadline
from app.nlp.keyword_extraction import analyze_text
from app.nlp.skill_extraction import (
    compute_skill_overlap,
    extract_programming_languages,
    extract_research_areas,
    extract_skills,
)

# ══════════════════════════════════════════════════════
# Keyword Extraction Tests
# ══════════════════════════════════════════════════════


class TestAnalyzeText:
    """Test the main NLP analysis function."""

    def test_detects_phd_opportunity(self):
        text = """
        PhD Position in Natural Language Processing
        We are looking for a highly motivated PhD student to work on
        large language models and NLP. Apply by January 15, 2025.
        The position is fully funded with a competitive stipend.
        """
        result = analyze_text(text)
        assert result.is_opportunity is True
        assert result.opportunity_type_hint == "PhD"

    def test_detects_internship(self):
        text = """
        Summer Research Internship 2025
        We are hiring research interns for the summer.
        Apply now for our machine learning internship program.
        Deadline: March 1, 2025.
        """
        result = analyze_text(text)
        assert result.is_opportunity is True
        assert result.opportunity_type_hint == "Internship"

    def test_detects_fellowship(self):
        text = """
        Research Fellowship in AI Safety
        Applications are open for our fellowship program.
        Fully funded for 12 months. Deadline is February 28, 2025.
        """
        result = analyze_text(text)
        assert result.is_opportunity is True
        assert result.opportunity_type_hint == "Fellowship"

    def test_rejects_non_opportunity(self):
        text = """
        Welcome to our department's homepage. We study various
        topics in computer science. Here are our recent publications
        and current research projects.
        """
        result = analyze_text(text)
        assert result.is_opportunity is False

    def test_extracts_programming_languages(self):
        text = "Candidates should be proficient in Python, PyTorch, and C++."
        result = analyze_text(text)
        assert "python" in result.programming_languages
        assert "c++" in result.programming_languages

    def test_extracts_skills(self):
        text = "Experience with Docker, Kubernetes, and TensorFlow required."
        result = analyze_text(text)
        assert "docker" in result.skills
        assert "kubernetes" in result.skills
        assert "tensorflow" in result.skills

    def test_extracts_research_areas(self):
        text = "Working on natural language processing and computer vision."
        result = analyze_text(text)
        assert "natural language processing" in result.research_areas
        assert "computer vision" in result.research_areas

    def test_extracts_deadline(self):
        text = "Deadline: January 15, 2025. Apply now!"
        result = analyze_text(text)
        assert result.deadline_str == "January 15, 2025"


# ══════════════════════════════════════════════════════
# Deadline Parser Tests
# ══════════════════════════════════════════════════════


class TestDeadlineParser:
    """Test deadline date parsing."""

    def test_parse_full_date(self):
        dt = parse_deadline("January 15, 2025")
        assert dt is not None
        assert dt.month == 1
        assert dt.day == 15
        assert dt.year == 2025

    def test_parse_short_date(self):
        dt = parse_deadline("15 Jan 2025")
        assert dt is not None
        assert dt.month == 1

    def test_parse_iso_date(self):
        dt = parse_deadline("2025-03-01")
        assert dt is not None
        assert dt.month == 3

    def test_parse_iso_datetime(self):
        dt = parse_deadline("2025-03-01T23:59:59Z")
        assert dt is not None
        assert dt.hour == 23

    def test_rolling_returns_none(self):
        assert parse_deadline("rolling") is None
        assert parse_deadline("open until filled") is None

    def test_none_input(self):
        assert parse_deadline(None) is None

    def test_garbage_input(self):
        assert parse_deadline("not a date at all xyz") is None

    def test_end_of_day_default(self):
        dt = parse_deadline("2025-06-15")
        assert dt is not None
        assert dt.hour == 23  # End of day

    def test_is_deadline_valid_future(self):
        future = datetime(2030, 1, 1, tzinfo=UTC)
        assert is_deadline_valid(future) is True

    def test_is_deadline_valid_past(self):
        past = datetime(2020, 1, 1, tzinfo=UTC)
        assert is_deadline_valid(past) is False

    def test_is_deadline_valid_none(self):
        assert is_deadline_valid(None) is True

    def test_days_until_deadline(self):
        future = datetime(2030, 1, 1, tzinfo=UTC)
        days = days_until_deadline(future)
        assert days is not None
        assert days > 0


# ══════════════════════════════════════════════════════
# Skill Extraction Tests
# ══════════════════════════════════════════════════════


class TestSkillExtraction:
    """Test skill extraction with alias normalization."""

    def test_extracts_direct_skills(self):
        skills = extract_skills("Experience with PyTorch and Docker required")
        assert "pytorch" in skills
        assert "docker" in skills

    def test_normalizes_aliases(self):
        skills = extract_skills("Must know Python3, TF, and K8s")
        assert "python" in skills
        assert "tensorflow" in skills
        assert "kubernetes" in skills

    def test_extracts_programming_languages(self):
        langs = extract_programming_languages("Proficient in Python, Java, and C++")
        assert "python" in langs
        assert "java" in langs
        assert "c++" in langs

    def test_extracts_research_areas(self):
        areas = extract_research_areas("Working on NLP and computer vision")
        assert "natural language processing" in areas
        assert "computer vision" in areas

    def test_research_area_aliases(self):
        areas = extract_research_areas("Focus on RL and FL techniques")
        assert "reinforcement learning" in areas
        assert "federated learning" in areas

    def test_skill_overlap_full_match(self):
        matched, missing, ratio = compute_skill_overlap(
            ["Python", "PyTorch"], ["Python", "PyTorch", "Docker"]
        )
        assert ratio == 1.0
        assert len(missing) == 0

    def test_skill_overlap_partial(self):
        matched, missing, ratio = compute_skill_overlap(["Python", "PyTorch", "C++"], ["Python"])
        assert "python" in matched
        assert "pytorch" in missing
        assert ratio == pytest.approx(1 / 3)

    def test_skill_overlap_no_required(self):
        _, _, ratio = compute_skill_overlap([], ["Python"])
        assert ratio == 1.0
