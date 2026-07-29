"""AI Assist API — Cover letter, email draft, reading list, and interview prep."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.agents.user_facing.application_assistant import ApplicationAssistantAgent

router = APIRouter(prefix="/assist", tags=["AI Assist"])


class AssistRequest(BaseModel):
    opportunity_id: str | None = None
    opportunity_title: str | None = None
    organization: str | None = None
    professor: str | None = None
    research_areas: list[str] | None = None
    required_skills: list[str] | None = None


@router.post("/cover-letter")
async def generate_cover_letter(req: AssistRequest, user: CurrentUser):
    """Generate a personalized AI cover letter for an opportunity."""
    assistant = ApplicationAssistantAgent()

    user_profile = {
        "full_name": user.full_name,
        "degree_level": user.degree_level,
        "university": user.university,
        "skills": [{"skill_name": s.skill_name} for s in (user.skills or [])],
    }

    opp_data = {
        "title": req.opportunity_title or "Research Position",
        "organization": req.organization or "Institution",
        "professor": req.professor or "Hiring Committee",
        "research_areas": req.research_areas or [],
        "required_skills": req.required_skills or [],
    }

    cover_letter = await assistant.generate_cover_letter(user_profile, opp_data)
    return {"cover_letter": cover_letter}


@router.post("/email-draft")
async def generate_email_draft(req: AssistRequest, user: CurrentUser):
    """Generate a cold outreach email draft to a professor/PI."""
    assistant = ApplicationAssistantAgent()

    user_profile = {
        "full_name": user.full_name,
        "degree_level": user.degree_level,
    }

    opp_data = {
        "title": req.opportunity_title or "Research Opening",
        "organization": req.organization or "your lab",
        "professor": req.professor or "Professor",
        "research_areas": req.research_areas or [],
    }

    draft = await assistant.generate_email_draft(user_profile, opp_data)
    return draft


@router.post("/interview-prep")
async def generate_interview_prep(req: AssistRequest, user: CurrentUser):
    """Generate a structured interview preparation plan."""
    assistant = ApplicationAssistantAgent()

    user_profile = {
        "full_name": user.full_name,
        "skills": [{"skill_name": s.skill_name} for s in (user.skills or [])],
    }

    opp_data = {
        "title": req.opportunity_title or "Research Position",
        "required_skills": req.required_skills or ["Python", "Machine Learning"],
        "research_areas": req.research_areas or ["AI"],
    }

    plan = await assistant.generate_interview_prep(user_profile, opp_data)
    return plan


@router.post("/reading-list")
async def generate_reading_list(req: AssistRequest):
    """Generate a curated research reading list for a position."""
    assistant = ApplicationAssistantAgent()

    opp_data = {
        "organization": req.organization or "Academic Institution",
        "research_areas": req.research_areas or ["Machine Learning"],
    }

    readings = await assistant.generate_reading_list(opp_data)
    return {"reading_list": readings}
