"""Pydantic schemas for recommendations and AI features."""

from uuid import UUID

from pydantic import BaseModel, Field

from app.models.schemas.opportunity import OpportunityBrief


class MatchExplanation(BaseModel):
    """Explanation for why an opportunity matches a user."""

    match_score: int = Field(..., ge=0, le=100, description="Match percentage 0-100")
    strengths: list[str] = Field(default=[], description="Reasons this is a good match")
    gaps: list[str] = Field(default=[], description="Areas for improvement")
    overall: str = Field(..., description="One-line summary")


class RecommendedOpportunity(BaseModel):
    """An opportunity with match scoring and explanation."""

    opportunity: OpportunityBrief
    match_score: int = Field(..., ge=0, le=100)
    explanation: MatchExplanation
    rank: int


class RecommendationResponse(BaseModel):
    """Paginated list of personalized recommendations."""

    recommendations: list[RecommendedOpportunity] = []
    total: int = 0
    page: int = 1


class CompareRequest(BaseModel):
    """Request to compare multiple opportunities."""

    opportunity_ids: list[UUID] = Field(..., min_length=2, max_length=5)


class CompareResponse(BaseModel):
    """Side-by-side comparison of opportunities."""

    opportunities: list[dict] = []
    comparison_summary: str = ""
    recommendation: str = ""


class CoverLetterRequest(BaseModel):
    """Request to generate a cover letter."""

    opportunity_id: UUID
    additional_context: str | None = None


class CoverLetterResponse(BaseModel):
    """Generated cover letter."""

    cover_letter: str
    opportunity_title: str
    organization: str


class EmailDraftRequest(BaseModel):
    """Request to draft a professor email."""

    opportunity_id: UUID
    purpose: str = "express interest"  # express interest, ask questions, follow up
    additional_context: str | None = None


class EmailDraftResponse(BaseModel):
    """Generated email draft."""

    subject: str
    body: str
    to_email: str | None = None
    professor_name: str | None = None


class EligibilityCheckResponse(BaseModel):
    """Eligibility analysis for a specific opportunity."""

    opportunity_id: UUID
    is_eligible: bool
    eligibility_score: int = Field(..., ge=0, le=100)
    met_criteria: list[str] = []
    unmet_criteria: list[str] = []
    suggestions: list[str] = []


class PreparationPlanResponse(BaseModel):
    """Personalized preparation roadmap."""

    opportunity_id: UUID
    plan: list[dict] = []  # [{week: 1, tasks: [...], resources: [...]}]
    timeline_weeks: int = 4
    key_skills_to_develop: list[str] = []
