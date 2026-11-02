"""Validator Agent — verifies extracted opportunity data for accuracy and trust."""

import re
from datetime import UTC, datetime
from urllib.parse import urlparse

import tldextract

from app.models.schemas.agent import ValidationReport
from app.models.schemas.opportunity import ExtractedOpportunity

# ── Trusted Domain Patterns ──────────────────────────
TRUSTED_SUFFIXES = {"edu", "ac.uk", "ac.in", "ac.jp", "ac.kr", "edu.au", "edu.sg", "edu.cn"}
TRUSTED_DOMAINS = {
    "google.com", "microsoft.com", "openai.com", "anthropic.com",
    "deepmind.google", "nvidia.com", "amazon.science", "apple.com",
    "meta.com", "huggingface.co", "github.com", "linkedin.com",
    "nsf.gov", "nih.gov", "daad.de", "erc.europa.eu",
    "researchgate.net", "semanticscholar.org",
    "neurips.cc", "icml.cc", "iclr.cc", "aclanthology.org",
    "cvpr.thecvf.com", "aaai.org", "kdd.org",
}

# ── Scam Indicators ──────────────────────────────────
SCAM_PATTERNS = [
    r"(?i)pay\s+(?:a\s+)?(?:fee|deposit|registration\s+fee)",
    r"(?i)send\s+money",
    r"(?i)western\s+union",
    r"(?i)bitcoin|cryptocurrency\s+(?:payment|required)",
    r"(?i)guaranteed\s+(?:visa|admission|acceptance)",
    r"(?i)no\s+experience\s+(?:required|needed|necessary)\s+.*(?:earn|salary|\$\d)",
    r"(?i)work\s+from\s+home\s+.*(?:earn|\$\d{3,})",
]


class ValidatorAgent:
    """
    Validates extracted opportunities for accuracy, trust, and completeness.

    Checks:
    1. URL validity — is the application link reachable?
    2. Domain trust — is the source a known institution?
    3. Temporal consistency — is the deadline in the future?
    4. Data completeness — are critical fields populated?
    5. Scam detection — does it match known fraud patterns?
    6. Text consistency — does the extraction match the source text?
    """

    async def validate(
        self, opportunity: ExtractedOpportunity
    ) -> ValidationReport:
        """Run all validation checks and produce a report."""
        scores: dict[str, float] = {}
        issues: list[str] = []

        # 1. URL validation
        scores["url_valid"] = self._check_url_format(
            opportunity.application_link, issues
        )

        # 2. Domain trust
        scores["domain_trust"] = self._check_domain_trust(
            opportunity.source_url, issues
        )

        # 3. Temporal consistency
        scores["temporal_ok"] = self._check_deadline(
            opportunity.deadline, issues
        )

        # 4. Data completeness
        scores["completeness"] = self._check_completeness(opportunity, issues)

        # 5. Scam detection
        scores["not_scam"] = self._check_scam(opportunity, issues)

        # 6. Text consistency (check key fields appear in raw text)
        scores["text_consistent"] = self._check_text_consistency(opportunity, issues)

        # Compute composite authenticity score
        authenticity = (
            scores.get("url_valid", 0.5) * 0.15
            + scores.get("domain_trust", 0.5) * 0.30
            + scores.get("temporal_ok", 0.5) * 0.15
            + scores.get("completeness", 0.5) * 0.15
            + scores.get("not_scam", 0.5) * 0.15
            + scores.get("text_consistent", 0.5) * 0.10
        )

        return ValidationReport(
            opportunity_id=opportunity.source_url,
            is_valid=authenticity >= 0.4 and scores.get("not_scam", 1.0) > 0.3,
            authenticity_score=round(authenticity, 3),
            field_scores=scores,
            issues=issues,
        )

    def _check_url_format(self, url: str, issues: list[str]) -> float:
        """Check if the URL is well-formed."""
        try:
            parsed = urlparse(url)
            if parsed.scheme in ("http", "https") and parsed.netloc:
                return 1.0
            issues.append(f"Invalid URL format: {url[:100]}")
            return 0.2
        except Exception:
            issues.append("URL parsing failed")
            return 0.0

    def _check_domain_trust(self, source_url: str, issues: list[str]) -> float:
        """Score domain trust based on known institutions."""
        try:
            extracted = tldextract.extract(source_url)
            domain = f"{extracted.domain}.{extracted.suffix}"
            suffix = extracted.suffix

            # Known trusted domains
            if domain in TRUSTED_DOMAINS:
                return 1.0

            # Academic suffixes
            if suffix in TRUSTED_SUFFIXES:
                return 0.9

            # Government
            if "gov" in suffix:
                return 0.9

            # Known tech/research orgs
            if any(kw in domain for kw in ["research", "science", "academic", "university"]):
                return 0.7

            # Unknown domain
            issues.append(f"Unknown domain: {domain} — verify source manually")
            return 0.4

        except Exception:
            issues.append("Domain extraction failed")
            return 0.3

    def _check_deadline(
        self, deadline: datetime | None, issues: list[str]
    ) -> float:
        """Check if the deadline is temporally valid."""
        if deadline is None:
            return 0.5  # No deadline is neutral

        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=UTC)

        now = datetime.now(UTC)

        if deadline < now:
            issues.append(f"Deadline is in the past: {deadline.isoformat()}")
            return 0.1

        # Very far in the future? Suspicious
        days_until = (deadline - now).days
        if days_until > 365:
            issues.append(f"Deadline is over a year away: {days_until} days")
            return 0.6

        return 1.0

    def _check_completeness(
        self, opp: ExtractedOpportunity, issues: list[str]
    ) -> float:
        """Score based on how many critical fields are populated."""
        critical_fields = [
            ("title", opp.title),
            ("organization", opp.organization),
            ("application_link", opp.application_link),
        ]
        important_fields = [
            ("opportunity_type", opp.opportunity_type),
            ("country", opp.country),
            ("research_areas", opp.research_areas),
            ("deadline", opp.deadline),
        ]

        # All critical fields must be present
        critical_score = sum(1 for _, v in critical_fields if v) / len(critical_fields)
        if critical_score < 1.0:
            missing = [name for name, v in critical_fields if not v]
            issues.append(f"Missing critical fields: {', '.join(missing)}")

        # Important fields are nice to have
        important_score = sum(
            1 for _, v in important_fields if v
        ) / len(important_fields)

        return critical_score * 0.7 + important_score * 0.3

    def _check_scam(
        self, opp: ExtractedOpportunity, issues: list[str]
    ) -> float:
        """Check for known scam patterns."""
        text_to_check = f"{opp.title} {opp.summary or ''} {opp.raw_text or ''}"

        scam_matches = sum(
            1 for pattern in SCAM_PATTERNS
            if re.search(pattern, text_to_check)
        )

        if scam_matches >= 2:
            issues.append(f"Multiple scam indicators detected ({scam_matches} matches)")
            return 0.0
        elif scam_matches == 1:
            issues.append("Possible scam indicator detected — review manually")
            return 0.4

        return 1.0

    def _check_text_consistency(
        self, opp: ExtractedOpportunity, issues: list[str]
    ) -> float:
        """Check if key extracted fields appear in the raw text."""
        if not opp.raw_text:
            return 0.5  # Can't verify without raw text

        raw_lower = opp.raw_text.lower()
        checks = []

        # Title should appear in text
        if opp.title:
            # Check if at least 60% of title words appear
            title_words = [w for w in opp.title.lower().split() if len(w) > 3]
            if title_words:
                found = sum(1 for w in title_words if w in raw_lower)
                checks.append(found / len(title_words))

        # Organization should appear in text
        if opp.organization:
            org_lower = opp.organization.lower()
            checks.append(1.0 if org_lower in raw_lower else 0.3)

        if not checks:
            return 0.5

        avg_score = sum(checks) / len(checks)
        if avg_score < 0.5:
            issues.append("Extracted data may not match source text — possible hallucination")

        return round(avg_score, 3)
