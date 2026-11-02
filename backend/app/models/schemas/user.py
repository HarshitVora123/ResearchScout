"""Pydantic schemas for user authentication and profile management."""

from datetime import date, datetime
from uuid import UUID
from urllib.parse import urlparse

from pydantic import BaseModel, EmailStr, Field, field_validator

# ── Auth Schemas ─────────────────────────────────────

class UserRegisterRequest(BaseModel):
    """Registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=200)

    @field_validator("password")
    @classmethod
    def bcrypt_byte_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be no more than 72 UTF-8 bytes")
        return value


class UserLoginRequest(BaseModel):
    """Login request."""

    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def bcrypt_byte_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be no more than 72 UTF-8 bytes")
        return value


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


# ── Profile Schemas ──────────────────────────────────

class UserProfileResponse(BaseModel):
    """User profile response."""

    id: UUID
    email: str
    full_name: str
    university: str | None = None
    degree_level: str | None = None
    gpa: float | None = None
    country: str | None = None
    preferred_countries: list[str] = []
    preferred_domains: list[str] = []
    career_goals: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    resume_url: str | None = None
    skills: list["SkillResponse"] = []
    publications: list["PublicationResponse"] = []
    projects: list["ProjectResponse"] = []
    research_interests: list["ResearchInterestResponse"] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdateRequest(BaseModel):
    """Profile update request."""

    full_name: str | None = None
    university: str | None = None
    degree_level: str | None = None
    gpa: float | None = Field(default=None, ge=0, le=4.0)
    country: str | None = None
    preferred_countries: list[str] | None = None
    preferred_domains: list[str] | None = None
    career_goals: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None

    @field_validator("linkedin_url", "github_url")
    @classmethod
    def validate_profile_urls(cls, value: str | None) -> str | None:
        if value is None:
            return value
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("URL must be an absolute HTTP(S) URL")
        return value


# ── Skill Schemas ────────────────────────────────────

class SkillResponse(BaseModel):
    """User skill response."""

    id: UUID
    skill_name: str
    proficiency: str | None = None
    years: int | None = None

    model_config = {"from_attributes": True}


class SkillCreateRequest(BaseModel):
    """Add a skill."""

    skill_name: str = Field(..., min_length=1, max_length=100)
    proficiency: str | None = None  # Beginner / Intermediate / Advanced / Expert
    years: int | None = Field(default=None, ge=0, le=50)


# ── Publication Schemas ──────────────────────────────

class PublicationResponse(BaseModel):
    """User publication response."""

    id: UUID
    title: str
    venue: str | None = None
    year: int | None = None
    url: str | None = None
    citation_count: int = 0

    model_config = {"from_attributes": True}


class PublicationCreateRequest(BaseModel):
    """Add a publication."""

    title: str = Field(..., min_length=1, max_length=500)
    venue: str | None = None
    year: int | None = Field(default=None, ge=1950, le=2030)
    url: str | None = None
    citation_count: int = Field(default=0, ge=0)


# ── Project Schemas ──────────────────────────────────

class ProjectResponse(BaseModel):
    """User project response."""

    id: UUID
    title: str
    description: str | None = None
    technologies: list[str] = []
    url: str | None = None
    start_date: date | None = None
    end_date: date | None = None

    model_config = {"from_attributes": True}


class ProjectCreateRequest(BaseModel):
    """Add a project."""

    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    technologies: list[str] = []
    url: str | None = None
    start_date: date | None = None
    end_date: date | None = None


# ── Research Interest Schemas ────────────────────────

class ResearchInterestResponse(BaseModel):
    """User research interest response."""

    id: UUID
    topic: str
    weight: float = 1.0

    model_config = {"from_attributes": True}


class ResearchInterestCreateRequest(BaseModel):
    """Add a research interest."""

    topic: str = Field(..., min_length=1, max_length=200)
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
