"""Extractor Agent — LLM-powered structured extraction from web content."""

import json
import re
from urllib.parse import urlparse

from app.config import get_settings
from app.models.schemas.opportunity import ExtractedOpportunity

settings = get_settings()

# ── Extraction Prompts ───────────────────────────────

EXTRACTION_SYSTEM_PROMPT = """You are an expert research opportunity information extractor.

Given a webpage's text content, extract structured information about research
opportunities (internships, PhD positions, fellowships, scholarships, summer schools, etc.).

Rules:
1. Extract ONLY information explicitly stated in the text. Never infer or hallucinate.
2. If a field is not mentioned, set it to null.
3. For deadlines, normalize to ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ).
4. For research areas, use standardized terms (e.g., "Natural Language Processing" not "NLP stuff").
5. Assign a confidence_score (0.0-1.0) based on how clearly the information was stated.
6. If the page lists MULTIPLE opportunities, extract ALL of them as separate objects.
7. If the page is NOT about a research opportunity, return an empty list.

Opportunity types to recognize:
- PhD, Masters Thesis, Internship, Research Assistant, Fellowship,
  Scholarship, Summer School, AI Residency, Postdoc, Undergraduate Research,
  Exchange Program, Government Project, Open Source Research

Return a JSON array of extracted opportunities."""

EXTRACTION_USER_TEMPLATE = """Extract research opportunities from the following webpage content.

Source URL: {url}
Page Title: {title}

--- Content ---
{content}
--- End Content ---

Return a JSON array of opportunity objects. If no opportunities found, return [].
"""


class ExtractorAgent:
    """
    Extracts structured ResearchOpportunity objects from raw web content.

    Uses LLM structured output with validation and confidence scoring.
    Supports multi-model fallback: Gemini Flash → GPT-4o → rule-based.
    """

    def __init__(self) -> None:
        self._openai_client = None
        self._google_client = None

    async def extract(
        self,
        content: str,
        url: str,
        title: str = "",
    ) -> list[ExtractedOpportunity]:
        """
        Extract research opportunities from content.

        Args:
            content: Markdown/text content from the crawler
            url: Source URL for attribution
            title: Page title

        Returns:
            List of extracted opportunities
        """
        if not content or len(content.strip()) < 100:
            return []

        # Truncate content for LLM context window
        truncated_content = content[:12000]

        rule_based = self._extract_rule_based(truncated_content, url, title)
        if rule_based:
            return rule_based

        try:
            # Try primary LLM (Gemini Flash for speed + cost)
            raw_json = await self._extract_with_gemini(truncated_content, url, title)
            if raw_json:
                return self._parse_results(raw_json, url)
        except Exception as e:
            print(f"Gemini extraction failed: {e}")

        try:
            # Fallback to OpenAI
            raw_json = await self._extract_with_openai(truncated_content, url, title)
            if raw_json:
                return self._parse_results(raw_json, url)
        except Exception as e:
            print(f"OpenAI extraction failed: {e}")

        # Deterministic extraction keeps discovery functional without an LLM key.
        # It only emits records when the page contains explicit opportunity signals.
        return self._extract_rule_based(truncated_content, url, title)

    @staticmethod
    def _extract_rule_based(
        content: str, url: str, page_title: str = ""
    ) -> list[ExtractedOpportunity]:
        """Extract a conservative single opportunity from explicit page text."""
        from app.nlp.keyword_extraction import analyze_text

        analysis = analyze_text(content)
        if not analysis.is_opportunity:
            return []

        opportunity_type = analysis.opportunity_type_hint or "Research Assistant"
        headings = [
            re.sub(r"[#*_`]+", "", line).strip(" -–—")
            for line in content.splitlines()
            if re.match(r"^\s{0,3}#{1,6}\s+", line)
        ]
        title = next(
            (
                heading[:200]
                for heading in headings
                if len(heading) >= 8
                and re.search(
                    (
                        r"ph\.?d|doctoral|intern|fellow|scholarship|research assistant|"
                        r"summer school|residen|position|opening|opportunit"
                    ),
                    heading,
                    re.IGNORECASE,
                )
            ),
            (page_title or (headings[0] if headings else "")).strip()[:200],
        )
        if len(title) < 8:
            return []

        host = (urlparse(url).hostname or "").removeprefix("www.")
        if not host:
            return []
        plain_content = re.sub(r"\s+", " ", re.sub(r"[#*_`>-]+", " ", content)).strip()
        return [
            ExtractedOpportunity(
                title=title,
                opportunity_type=opportunity_type,
                organization=host,
                research_areas=analysis.research_areas,
                keywords=analysis.keywords,
                required_skills=analysis.skills,
                programming_languages=analysis.programming_languages,
                application_link=url,
                source_url=url,
                summary=plain_content[:500] or None,
                raw_text=content[:5000],
                confidence_score=0.55,
            )
        ]

    async def _extract_with_gemini(self, content: str, url: str, title: str) -> str | None:
        """Extract using Google Gemini Flash."""
        if not settings.google_api_key:
            return None

        import google.genai as genai

        client = genai.Client(api_key=settings.google_api_key)

        prompt = EXTRACTION_USER_TEMPLATE.format(url=url, title=title, content=content)

        import asyncio

        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=[
                {
                    "role": "user",
                    "parts": [{"text": EXTRACTION_SYSTEM_PROMPT + "\n\n" + prompt}],
                }
            ],
            config={"response_mime_type": "application/json", "temperature": 0.1},
        )

        return response.text if response.text else None

    async def _extract_with_openai(self, content: str, url: str, title: str) -> str | None:
        """Extract using OpenAI GPT-4o."""
        if not settings.openai_api_key:
            return None

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)

        prompt = EXTRACTION_USER_TEMPLATE.format(url=url, title=title, content=content)

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        return response.choices[0].message.content

    def _parse_results(self, raw_json: str, source_url: str) -> list[ExtractedOpportunity]:
        """Parse LLM JSON output into typed Pydantic models."""
        try:
            data = json.loads(raw_json)

            # Handle both {"opportunities": [...]} and [...] formats
            if isinstance(data, dict):
                items = data.get("opportunities", data.get("results", []))
            elif isinstance(data, list):
                items = data
            else:
                return []

            opportunities = []
            for item in items or []:
                try:
                    # Ensure source_url is set
                    item["source_url"] = item.get("source_url", source_url)
                    item["application_link"] = item.get("application_link", source_url)
                    opp = ExtractedOpportunity.model_validate(item)
                    opportunities.append(opp)
                except Exception as e:
                    print(f"Failed to parse opportunity: {e}")
                    continue

            return opportunities

        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM JSON: {e}")
            return []
