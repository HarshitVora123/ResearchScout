"""
Resume Parser — extracts structured profile data from text or PDF resumes.

Extracts:
- Contact information (email, name, phone)
- Education (university, degree level, major/field of study, GPA)
- Technical skills & programming languages
- Research interests & topics
- Publications & projects
- Experience years estimate
"""

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import structlog

from app.nlp.skill_extraction import extract_programming_languages, extract_skills

logger = structlog.get_logger(__name__)


@dataclass
class ParsedResume:
    """Structured data extracted from a resume."""

    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    university: str | None = None
    degree_level: str | None = None  # Bachelor, Master, PhD, Postdoc
    major: str | None = None  # e.g. "Computer Science", "Data Science"
    gpa: float | None = None
    experience_years: int = 0
    skills: list[str] = field(default_factory=list)
    programming_languages: list[str] = field(default_factory=list)
    research_interests: list[str] = field(default_factory=list)
    publications: list[dict[str, Any]] = field(default_factory=list)
    projects: list[dict[str, Any]] = field(default_factory=list)
    raw_text: str = ""


# Regex patterns for contact & education info
EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
PHONE_REGEX = r"(\+?\d{1,3}[\s-]?)?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{4}"
GPA_REGEX = r"(?:GPA|CGPA)[:\s]*([0-9]{1,2}(?:\.\d{1,2})?)(?:\s*/\s*(10(?:\.0)?|4(?:\.0{1,2})?))?"

DEGREE_PATTERNS = {
    "PhD": [r"\bph\.?d\b", r"\bdoctorate\b", r"\bdoctor of philosophy\b"],
    "Master": [r"\bm\.?s\.?\b", r"\bm\.?tech\b", r"\bmaster'?s?\b", r"\bm\.?sc\b"],
    "Bachelor": [
        r"\bb\.?s\.?\b",
        r"\bb\.?tech\b",
        r"\bbachelor'?s?\b",
        r"\bb\.?sc\b",
        r"\bb\.?e\.?\b",
    ],
    "Postdoc": [r"\bpostdoc\b", r"\bpostdoctoral\b"],
}

UNIVERSITY_KEYWORDS = [
    "university",
    "institute",
    "college",
    "polytechnic",
    "eth zürich",
    "eth zurich",
    "epfl",
    "mit",
    "stanford",
    "harvard",
    "cmu",
    "berkeley",
    "oxford",
    "cambridge",
    "iit",
    "tsinghua",
    "ntu",
    "nus",
]

# Major / Field of Study patterns
MAJOR_PATTERNS = [
    # "B.S. in Computer Science", "Master of Data Science"
    r"(?:in|of)\s+([\w\s&/]+?)(?:\s*(?:from|at|,|\.))",
    # "Major: Computer Science"
    r"(?:major|specialization|concentration|field)[:\s]+(.+?)(?:\n|,|\.)",
    # "Computer Science and Engineering" near degree keyword
    r"(?:degree|bachelor|master|ph\.?d|b\.?tech|m\.?tech)\w*\s+(?:in|of)\s+([\w\s&/]+?)(?:\s*(?:from|at|,|\.|$))",
]

# Common CS/Engineering majors for matching
KNOWN_MAJORS = [
    "computer science",
    "data science",
    "machine learning",
    "electrical engineering",
    "computer engineering",
    "information technology",
    "software engineering",
    "statistics",
    "mathematics",
    "applied mathematics",
    "physics",
    "bioinformatics",
    "computational biology",
    "neuroscience",
    "robotics",
    "mechatronics",
    "biomedical engineering",
    "chemical engineering",
    "mechanical engineering",
    "economics",
    "business analytics",
    "artificial intelligence and data science",
    "artificial intelligence",
    "computer vision",
    "information retrieval",
]

# Experience section year patterns
YEAR_RANGE_REGEX = r"(20\d{2})\s*[-–—]\s*(20\d{2}|present|current|now)"


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
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if lines:
            first_line = lines[0]
            if (
                len(first_line) < 50
                and "@" not in first_line
                and not any(c in first_line for c in "0123456789")
            ):
                parsed.full_name = first_line

        # 3. GPA
        gpa_match = re.search(GPA_REGEX, text, re.IGNORECASE)
        if gpa_match:
            try:
                value = float(gpa_match.group(1))
                # Indian resumes commonly omit "/10" for CGPA values such as 9.60.
                denominator = float(gpa_match.group(2) or (10 if value > 4 else 4))
                if denominator == 10:
                    value = value * 4 / 10
                parsed.gpa = min(value, 4.0)
            except ValueError:
                pass

        # 4. Degree Level
        for degree, patterns in DEGREE_PATTERNS.items():
            if any(re.search(pat, text, re.IGNORECASE) for pat in patterns):
                parsed.degree_level = degree
                break

        # 5. University: prioritize the Education section and remove inline GPA.
        education_lines = self._section_lines(lines, {"education", "academic background"})
        for line in education_lines or lines[:15]:
            line_lower = line.lower()
            if any(kw in line_lower for kw in UNIVERSITY_KEYWORDS):
                university = re.split(r"\b(?:c?gpa|gpa)\s*[:\-]", line, flags=re.IGNORECASE)[0]
                university = re.sub(r"\s{2,}", " ", university).strip(" |,–-\t")
                if university:
                    parsed.university = university[:100]
                break

        # 6. Major / Field of Study
        parsed.major = self._extract_major(text, lines)

        # 7. Skills & Programming Languages
        from app.nlp.skill_extraction import extract_programming_languages, extract_research_areas

        parsed.skills = extract_skills(text)
        parsed.programming_languages = extract_programming_languages(text)
        parsed.research_interests = extract_research_areas(text)

        # 8. Experience years estimate
        parsed.experience_years = self._estimate_experience_years(text)

        # 9. Publications and projects grouped by their section headings.
        publication_lines = self._section_lines(
            lines, {"publications", "selected publications", "papers"}
        )
        for line in publication_lines:
            cleaned = self._clean_bullet(line)
            if len(cleaned) >= 20 and not self._is_section_heading(cleaned):
                parsed.publications.append({"title": cleaned[:200]})
            if len(parsed.publications) == 10:
                break

        project_lines = self._section_lines(
            lines, {"projects", "selected projects", "research projects", "academic projects"}
        )
        parsed.projects = self._parse_projects(project_lines)

        logger.info(
            "resume_parsed",
            degree=parsed.degree_level,
            major=parsed.major,
            skills_count=len(parsed.skills),
            experience_years=parsed.experience_years,
        )

        return parsed

    @staticmethod
    def _heading_key(line: str) -> str:
        return re.sub(r"[^a-z ]", "", line.lower()).strip()

    @classmethod
    def _is_section_heading(cls, line: str) -> bool:
        headings = {
            "education",
            "academic background",
            "experience",
            "work experience",
            "professional experience",
            "projects",
            "selected projects",
            "research projects",
            "academic projects",
            "publications",
            "selected publications",
            "papers",
            "technical skills",
            "skills",
            "skills languages",
            "leadership activities",
            "awards",
            "certifications",
            "research experience",
        }
        return cls._heading_key(line) in headings

    @classmethod
    def _section_lines(cls, lines: list[str], section_names: set[str]) -> list[str]:
        section_keys = {cls._heading_key(name) for name in section_names}
        started = False
        result: list[str] = []
        for line in lines:
            key = cls._heading_key(line)
            if not started:
                if key in section_keys:
                    started = True
                continue
            if cls._is_section_heading(line):
                break
            result.append(line)
        return result

    @staticmethod
    def _clean_bullet(line: str) -> str:
        return re.sub(r"^\s*(?:[•●▪◦‣–—-]+|\d+[.)])\s*", "", line).strip()

    @staticmethod
    def _looks_like_project_title(line: str) -> bool:
        """Distinguish short title-cased headings from wrapped description lines."""
        if len(line) > 120 or re.search(r"[.!?;:]$", line):
            return False
        words = re.findall(r"[A-Za-z][A-Za-z'-]*", line)
        if len(words) < 2:
            return False
        title_case_ratio = sum(word[0].isupper() for word in words) / len(words)
        return title_case_ratio >= 0.65

    def _parse_projects(self, lines: list[str]) -> list[dict[str, Any]]:
        projects: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        descriptions: list[str] = []
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            cleaned = self._clean_bullet(line)
            if re.match(r"^(?:research\s+)?advisor\s*:", cleaned, re.IGNORECASE):
                continue
            is_bullet = cleaned != line or line.startswith(("•", "●", "▪", "◦", "‣", "–", "—", "-"))
            # Project titles are concise and title-cased. PDF text extraction
            # drops bold styling, so wrapped sentence lines are attached to the
            # current project's description instead of becoming fake projects.
            is_title = current is None or self._looks_like_project_title(cleaned)
            is_status_only = re.match(r"^(?:ongoing|in progress|\d{4})\b", cleaned, re.IGNORECASE)
            if not is_bullet and is_title and not is_status_only:
                if current:
                    current["description"] = " ".join(descriptions).strip() or None
                    block = f"{current['title']} {current.get('description') or ''}"
                    current["technologies"] = sorted(
                        set(extract_skills(block) + extract_programming_languages(block))
                    )
                    projects.append(current)
                title = re.sub(
                    r"\s+(?:ongoing|in progress|present)$", "", cleaned, flags=re.IGNORECASE
                ).strip(" |–—-")
                if len(title) >= 4:
                    current = {"title": title[:200]}
                    descriptions = []
                    if title != cleaned:
                        current["status"] = "Ongoing"
                continue
            if current and len(cleaned) > 10:
                descriptions.append(cleaned)
        if current:
            current["description"] = " ".join(descriptions).strip() or None
            block = f"{current['title']} {current.get('description') or ''}"
            current["technologies"] = sorted(
                set(extract_skills(block) + extract_programming_languages(block))
            )
            projects.append(current)
        return projects[:20]

    def _extract_major(self, text: str, lines: list[str]) -> str | None:
        """Extract major/field of study from resume text."""
        for line in self._section_lines(lines, {"education", "academic background"}):
            match = re.search(
                r"\b(?:b\.?e\.?|b\.?tech|bachelor'?s?)\s*[–—-]\s*(.+?)(?:\s+(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+)?\d{4}\b|$)",
                line,
                re.IGNORECASE,
            )
            if match and 3 < len(match.group(1).strip()) <= 80:
                return match.group(1).strip(" .–—-").title()

        # Try regex patterns first
        for pattern in MAJOR_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                # Validate it looks like a real major (not too long, not too short)
                if 3 < len(candidate) < 60:
                    return candidate.title()

        # Fallback: look for known majors in the text
        text_lower = text.lower()
        for major in KNOWN_MAJORS:
            if major in text_lower:
                return major.title()

        return None

    def _estimate_experience_years(self, text: str) -> int:
        """Estimate total years of experience from date ranges in the resume."""
        total_years = 0
        for match in re.finditer(YEAR_RANGE_REGEX, text, re.IGNORECASE):
            start = int(match.group(1))
            end_str = match.group(2).lower()
            end = date.today().year if end_str in ("present", "current", "now") else int(end_str)
            years = max(0, end - start)
            total_years += years
        return min(total_years, 30)  # Cap at 30 years
