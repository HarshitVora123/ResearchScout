"""
Application Assistant Agent — AI tools for research opportunity applicants:
- AI Cover Letter Generator
- AI Email Drafter (Outreach to Professors & PIs)
- Research Reading List Generator
- Interview Preparation Planner
"""

from typing import Any

import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class ApplicationAssistantAgent:
    """
    Generates tailored application materials and preparation plans using LLMs.
    """

    async def generate_cover_letter(
        self,
        user_profile: dict[str, Any],
        opportunity: dict[str, Any],
    ) -> str:
        """
        Generate a personalized academic cover letter tailored to a specific position.
        """
        user_name = user_profile.get("full_name", "Researcher")
        university = user_profile.get("university", "my university")
        degree = user_profile.get("degree_level", "my degree")
        skills = [
            s["skill_name"] if isinstance(s, dict) else s
            for s in user_profile.get("skills", [])
        ]

        title = opportunity.get("title", "Research Position")
        org = opportunity.get("organization", "your institution")
        prof = opportunity.get("professor", "Hiring Committee")
        areas = opportunity.get("research_areas", [])

        # Call LLM if API key available, otherwise generate structured draft
        if settings.google_api_key or settings.openai_api_key:
            try:
                return await self._llm_generate_cover_letter(user_profile, opportunity)
            except Exception as e:
                logger.warning("llm_cover_letter_failed", error=str(e))

        # High-quality fallback template
        skills_str = ", ".join(skills[:4]) if skills else "relevant research methodologies"
        areas_str = ", ".join(areas[:2]) if areas else "this field"

        return f"""Dear {prof},

I am writing to express my strong interest in the {title} position at {org}. Having recently pursued my {degree} at {university}, I have built a solid foundation in {areas_str}.

My background aligns closely with the key requirements of this role. In particular, I have hands-on experience in {skills_str}. My research focus has centered on solving core challenges in {areas_str}, and I am eager to bring this expertise to your team at {org}.

I am particularly drawn to {org}'s work in {areas_str}. The opportunity to contribute to your ongoing projects is an exciting next step in my academic career.

Thank you for your time and consideration. I welcome the opportunity to discuss how my qualifications align with the needs of your group.

Sincerely,

{user_name}
"""

    async def generate_email_draft(
        self,
        user_profile: dict[str, Any],
        opportunity: dict[str, Any],
    ) -> dict[str, str]:
        """
        Generate a concise, professional cold outreach email draft to a professor/PI.
        """
        user_name = user_profile.get("full_name", "Prospective Student")
        degree = user_profile.get("degree_level", "student")
        prof = opportunity.get("professor", "Professor")
        org = opportunity.get("organization", "your lab")
        title = opportunity.get("title", "Research Position")
        areas = opportunity.get("research_areas", ["AI"])

        subject = f"Inquiry regarding {title} - {user_name}"

        body = f"""Dear Professor {prof.split()[-1] if prof and ' ' in prof else prof},

I hope this email finds you well.

My name is {user_name}, and I am currently a {degree} candidate interested in research opportunities in {', '.join(areas[:2])}.

I recently came across the open {title} at {org} and was deeply inspired by your lab's focus. My previous work has focused on {', '.join(areas[:2])}, and I believe my background would allow me to contribute effectively to your ongoing projects.

Would you have 10-15 minutes for a brief call to discuss potential research openings in your group for the upcoming term? I have attached my CV for your review.

Thank you for your time and consideration.

Best regards,

{user_name}
"""
        return {"subject": subject, "body": body}

    async def generate_reading_list(
        self,
        opportunity: dict[str, Any],
    ) -> list[dict[str, str]]:
        """
        Generate a curated reading list of foundational & recent papers
        to prepare for applying or interviewing.
        """
        areas = opportunity.get("research_areas", ["Machine Learning"])
        org = opportunity.get("organization", "Academic Institution")

        readings = []
        for area in areas[:3]:
            readings.append({
                "topic": area,
                "recommended_reading": f"Foundational Methods & Survey Papers in {area}",
                "description": f"Core literature and recent benchmark papers in {area} relevant to research at {org}.",
            })

        if not readings:
            readings.append({
                "topic": "General Methodology",
                "recommended_reading": "Key Publications in the Field",
                "description": "Essential literature review prior to interview.",
            })

        return readings

    async def generate_interview_prep(
        self,
        user_profile: dict[str, Any],
        opportunity: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate a structured interview preparation plan (technical questions,
        behavioral strategies, and questions to ask the professor).
        """
        title = opportunity.get("title", "Research Position")
        skills = opportunity.get("required_skills", ["Python", "Machine Learning"])
        areas = opportunity.get("research_areas", ["Artificial Intelligence"])

        questions = []
        for skill in skills[:3]:
            questions.append(f"Can you walk us through a recent project where you used {skill} to solve a complex problem?")

        for area in areas[:2]:
            questions.append(f"What are the major open challenges in {area} that you are most excited to address?")

        questions.extend([
            "How do you approach debugging when a research hypothesis or model fails to perform?",
            "Can you discuss a paper in your field that influenced your technical thinking recently?",
        ])

        questions_for_pi = [
            f"What are the primary active milestones for the lab over the next 12 months?",
            "How do graduate students and postdocs in the group collaborate on publication submissions?",
            "What compute resources and dataset access are available for this project?",
        ]

        return {
            "position": title,
            "technical_questions": questions,
            "questions_to_ask_pi": questions_for_pi,
            "prep_strategy": (
                "1. Re-read 2-3 recent publications from the PI/lab.\n"
                "2. Be ready to explain your past projects in 2 minutes (Problem -> Approach -> Result).\n"
                "3. Review core algorithms behind your listed skills."
            ),
        }

    async def _llm_generate_cover_letter(self, user_profile: dict, opportunity: dict) -> str:
        """Generate cover letter using Gemini Flash."""
        import google.genai as genai

        client = genai.Client(api_key=settings.google_api_key)
        prompt = f"""Write a professional 4-paragraph academic cover letter.
User Profile: {user_profile}
Opportunity Details: {opportunity}
Keep it concise, compelling, and academic.
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text
