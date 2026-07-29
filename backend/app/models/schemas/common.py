"""Common Pydantic schemas shared across the API."""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────

class OpportunityType(str, Enum):
    PHD = "PhD"
    MASTERS_THESIS = "Masters Thesis"
    INTERNSHIP = "Internship"
    RESEARCH_ASSISTANT = "Research Assistant"
    FELLOWSHIP = "Fellowship"
    SCHOLARSHIP = "Scholarship"
    SUMMER_SCHOOL = "Summer School"
    AI_RESIDENCY = "AI Residency"
    POSTDOC = "Postdoc"
    UNDERGRADUATE_RESEARCH = "Undergraduate Research"
    EXCHANGE_PROGRAM = "Exchange Program"
    GOVERNMENT_PROJECT = "Government Project"
    OPEN_SOURCE = "Open Source Research"
    OTHER = "Other"


class LocationType(str, Enum):
    REMOTE = "Remote"
    HYBRID = "Hybrid"
    ONSITE = "Onsite"
    UNKNOWN = "Unknown"


class FundingType(str, Enum):
    FULLY_FUNDED = "Fully Funded"
    PARTIAL = "Partial"
    SELF_FUNDED = "Self-funded"
    UNKNOWN = "Unknown"


class DegreeLevel(str, Enum):
    HIGH_SCHOOL = "High School"
    UNDERGRADUATE = "Undergraduate"
    MASTERS = "Masters"
    PHD = "PhD"
    POSTDOC = "Postdoc"
    ANY = "Any"


class InteractionType(str, Enum):
    VIEW = "view"
    SAVE = "save"
    APPLY = "apply"
    DISMISS = "dismiss"
    SHARE = "share"


class FeedbackType(str, Enum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    CORRECTION = "correction"
    REPORT = "report"


class SavedStatus(str, Enum):
    SAVED = "saved"
    APPLYING = "applying"
    APPLIED = "applied"
    REJECTED = "rejected"
    ACCEPTED = "accepted"


# ── Common Response Models ───────────────────────────

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    items: list = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    status_code: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str
