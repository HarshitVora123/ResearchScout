"""SQLAlchemy ORM models for users, skills, publications, projects, and interests."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    """Platform user with profile information."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Academic ─────────────────────────────────
    university: Mapped[str | None] = mapped_column(Text)
    degree_level: Mapped[str | None] = mapped_column(String(30))  # Undergraduate, Masters, PhD
    gpa: Mapped[float | None] = mapped_column(Numeric(3, 2))
    country: Mapped[str | None] = mapped_column(Text)

    # ── Preferences ──────────────────────────────
    preferred_countries: Mapped[list[str] | None] = mapped_column(JSON)
    preferred_domains: Mapped[list[str] | None] = mapped_column(JSON)
    career_goals: Mapped[str | None] = mapped_column(Text)

    # ── Profiles ─────────────────────────────────
    linkedin_url: Mapped[str | None] = mapped_column(Text)
    github_url: Mapped[str | None] = mapped_column(Text)
    resume_url: Mapped[str | None] = mapped_column(Text)  # MinIO path

    # ── Parsed profile text (for embedding) ──────
    parsed_resume_text: Mapped[str | None] = mapped_column(Text)

    # ── Audit ────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ────────────────────────────
    skills: Mapped[list["UserSkill"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    publications: Mapped[list["UserPublication"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    projects: Mapped[list["UserProject"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    research_interests: Mapped[list["UserResearchInterest"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.email!r}>"


class UserSkill(Base):
    """A skill associated with a user."""

    __tablename__ = "user_skills"
    __table_args__ = (UniqueConstraint("user_id", "skill_name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    skill_name: Mapped[str] = mapped_column(Text, nullable=False)
    proficiency: Mapped[str | None] = mapped_column(
        String(20)
    )  # Beginner / Intermediate / Advanced / Expert
    years: Mapped[int | None] = mapped_column(Integer)

    user: Mapped["User"] = relationship(back_populates="skills")

    def __repr__(self) -> str:
        return f"<UserSkill {self.skill_name!r}>"


class UserPublication(Base):
    """A publication authored or co-authored by the user."""

    __tablename__ = "user_publications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    venue: Mapped[str | None] = mapped_column(Text)
    year: Mapped[int | None] = mapped_column(Integer)
    url: Mapped[str | None] = mapped_column(Text)
    citation_count: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped["User"] = relationship(back_populates="publications")

    def __repr__(self) -> str:
        return f"<UserPublication {self.title!r}>"


class UserProject(Base):
    """A project completed by the user."""

    __tablename__ = "user_projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    technologies: Mapped[list[str] | None] = mapped_column(JSON)
    url: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)

    user: Mapped["User"] = relationship(back_populates="projects")

    def __repr__(self) -> str:
        return f"<UserProject {self.title!r}>"


class UserResearchInterest(Base):
    """A research topic the user is interested in."""

    __tablename__ = "user_research_interests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[float] = mapped_column(Numeric(3, 2), default=1.0)

    user: Mapped["User"] = relationship(back_populates="research_interests")

    def __repr__(self) -> str:
        return f"<UserResearchInterest {self.topic!r}>"
