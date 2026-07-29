"""Pydantic schemas for research opportunities — API contracts."""

import json
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.models.schemas.common import (
    FundingType,
    LocationType,
    OpportunityType,
)


def _robust_parse_list(v):
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            if isinstance(parsed, str):
                parsed = json.loads(parsed)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
    elif isinstance(v, list):
        if len(v) > 0 and isinstance(v[0], str) and (v[0] == "[" or v[0] == '"'):
            joined = "".join(v)
            try:
                parsed = json.loads(joined)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        return v
    return v or []


# ── Response Schemas ─────────────────────────────────

class OpportunityBrief(BaseModel):
    """Brief opportunity info for list views."""

    id: UUID
    title: str
    opportunity_type: str
    organization: str
    country: str | None = None
    city: str | None = None
    location_type: str | None = None
    research_areas: list[str] = []
    funding_type: str | None = None
    deadline: datetime | None = None
    summary: str | None = None
    confidence_score: float = 0.5
    date_discovered: datetime
    is_active: bool = True

    model_config = {"from_attributes": True}

    @field_validator("research_areas", mode="before")
    @classmethod
    def parse_json_list(cls, v):
        return _robust_parse_list(v)


class OpportunityDetail(BaseModel):
    """Full opportunity detail for detail views."""

    id: UUID
    title: str
    opportunity_type: str
    organization: str
    department: str | None = None
    research_lab: str | None = None
    professor: str | None = None
    professor_email: str | None = None

    country: str | None = None
    city: str | None = None
    location_type: str | None = None

    research_areas: list[str] = []
    keywords: list[str] = []
    required_skills: list[str] = []
    programming_languages: list[str] = []

    required_gpa: float | None = None
    eligibility_criteria: dict | None = None
    degree_levels: list[str] = []
    publications_required: bool = False
    recommendation_letters: int | None = None
    visa_requirements: str | None = None

    funding_type: str | None = None
    salary_range: str | None = None
    stipend: str | None = None

    duration: str | None = None
    deadline: datetime | None = None
    start_date: datetime | None = None

    application_link: str
    documents_required: list[str] = []
    contact_email: str | None = None

    source_url: str
    date_discovered: datetime
    last_verified: datetime | None = None
    confidence_score: float = 0.5
    authenticity_score: float = 0.5
    is_active: bool = True
    summary: str | None = None

    model_config = {"from_attributes": True}

    @field_validator("research_areas", "keywords", "required_skills", "programming_languages", "degree_levels", "documents_required", mode="before")
    @classmethod
    def parse_json_lists(cls, v):
        return _robust_parse_list(v)


# ── Request / Filter Schemas ─────────────────────────

class OpportunityFilters(BaseModel):
    """Query filters for browsing opportunities."""

    opportunity_type: list[str] | None = None
    country: list[str] | None = None
    research_areas: list[str] | None = None
    required_skills: list[str] | None = None
    funding_type: list[str] | None = None
    location_type: list[str] | None = None
    degree_level: list[str] | None = None
    min_confidence: float | None = None
    deadline_before: datetime | None = None
    deadline_after: datetime | None = None
    is_active: bool = True
    query: str | None = None  # Full-text search query

    # Pagination
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedOpportunities(BaseModel):
    """Paginated wrapper for opportunities list."""

    items: list[OpportunityBrief]
    total: int
    page: int
    page_size: int
    total_pages: int


class ExtractedOpportunity(BaseModel):
    """Schema for LLM-extracted opportunity data (pre-validation)."""

    title: str
    opportunity_type: str
    organization: str
    department: str | None = None
    research_lab: str | None = None
    professor: str | None = None
    professor_email: str | None = None

    country: str | None = None
    city: str | None = None
    location_type: str | None = None

    research_areas: list[str] = []
    keywords: list[str] = []
    required_skills: list[str] = []
    programming_languages: list[str] = []

    required_gpa: float | None = None
    eligibility_criteria: str | None = None
    degree_levels: list[str] = []
    publications_required: bool = False
    recommendation_letters: int | None = None
    visa_requirements: str | None = None

    funding_type: str | None = None
    salary_range: str | None = None
    stipend: str | None = None

    duration: str | None = None
    deadline: datetime | None = None
    start_date: datetime | None = None

    application_link: str
    documents_required: list[str] = []
    contact_email: str | None = None

    source_url: str
    summary: str | None = None
    raw_text: str | None = None
    confidence_score: float = 0.5
