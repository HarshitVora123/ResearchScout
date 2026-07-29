"""
Resume Parser — extracts structured profile data from text or PDF resumes.

Extracts:
- Contact information (email, name, phone)
- Education (university, degree level, major, GPA)
- Technical skills & programming languages
- Research interests & topics
- Publications & projects
"""

import re
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.nlp.skill_extraction import extract_skills

logger = structlog.get_logger(__name__)


@dataclass
class ParsedResume:
    """Structured data extracted from a resume."""

    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    university: str | None = None
    degree_level: str | None = None  # Bachelor, Master, PhD, Postdoc
    gpa: float | None = None
    skills: list[str] = field(default_factory=list)
    programming_languages: list[str] = field(default_factory=list)
    research_interests: list[str] = field(default_factory=list)
    publications: list[dict[str, Any]] = field(default_factory=list)
    projects: list[dict[str, Any]] = field(default_factory=list)
    raw_text: str = ""


# Regex patterns for contact & education info
EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
PHONE_REGEX = r"(\+?\d{1,3}[\s-]?)?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{4}"
GPA_REGEX = r"(?:GPA|gpa|cgpa|CGPA)[:\s]*([0-3]\.\d{1,2}|4\.0{1,2}|[0-9]\.\d{1,2}\s*/\s*10(?:\.0)?)"

DEGREE_PATTERNS = {
    "PhD": [r"\bph\.?d\b", r"\bdoctorate\b", r"\bdoctor of philosophy\b"],
    "Master": [r"\bm\.?s\.?\b", r"\bm\.?tech\b", r"\bmaster'?s?\b", r"\bm\.?sc\b"],
    "Bachelor": [r"\bb\.?s\.?\b", r"\bb\.?tech\b", r"\bbachelor'?s?\b", r"\bb\.?sc\b"],
    "Postdoc": [r"\bpostdoc\b", r"\bpostdoctoral\b"],
}

UNIVERSITY_KEYWORDS = [
    "university", "institute", "college", "polytechnic", "eth zürich",
    "eth zurich", "epfl", "mit", "stanford", "harvard", "cmu", "berkeley",
    "oxford", "cambridge", "iit", "tsinghua", "ntu", "nus",
]


class ResumeParser:
    """Parses resume text into a structured profile."""

    def parse_text(self, text: str) -> ParsedResume:
        """Parse raw resume text."""
        parsed = ParsedResume(raw_text=text[:10000])

        # 1. Contact info
        email_match = re.search(EMAIL_REGEX, text)
        if email_match:
            parsed.email = email_match.group(0)

        phone_match = re.search(PHONE_REGEX, text)
        if phone_match:
            parsed.phone = phone_match.group(0)

        # 2. Extract name (first non-empty line or line before email)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if lines:
            first_line = lines[0]
            if len(first_line) < 50 and not "@" in first_line and not any(c in first_line for c in "0123456789"):
                parsed.full_name = first_line

        # 3. GPA
        gpa_match = re.search(GPA_REGEX, text, re.IGNORECASE)
        if gpa_match:
            try:
                val_str = gpa_match.group(1).split("/")[0].strip()
                parsed.gpa = min(float(val_str), 4.0)
            except ValueError:
                pass

        # 4. Degree Level
        for degree, patterns in DEGREE_PATTERNS.items():
            if any(re.search(pat, text, re.IGNORECASE) for pat in patterns):
                parsed.degree_level = degree
                break

        # 5. University
        for line in lines[:15]:  # Look near top for education
            line_lower = line.lower()
            if any(kw in line_lower for kw in UNIVERSITY_KEYWORDS):
                parsed.university = line[:100]
                break

        # 6. Skills & Programming Languages
        from app.nlp.skill_extraction import extract_programming_languages, extract_research_areas
        parsed.skills = extract_skills(text)
        parsed.programming_languages = extract_programming_languages(text)
        parsed.research_interests = extract_research_areas(text)

        # 7. Publications heuristic
        pub_lines = []
        in_pub_section = False
        for line in lines:
            line_lower = line.lower()
            if "publication" in line_lower or "papers" in line_lower:
                in_pub_section = True
                continue
            if in_pub_section:
                if any(sec in line_lower for sec in ["experience", "education", "project", "skill", "award"]):
                    in_pub_section = False
                    continue
                if len(line) > 20:
                    pub_lines.append(line)

        for pub_text in pub_lines[:5]:
            parsed.publications.append({"title": pub_text[:200]})

        logger.info(
            "resume_parsed",
            name=parsed.full_name,
            degree=parsed.degree_level,
            skills_count=len(parsed.skills),
        )

        return parsed
