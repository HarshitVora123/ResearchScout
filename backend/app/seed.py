"""
Database Seeder — seeds sample research opportunities and a demo user into the database.
Run with: python -m app.seed
"""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import structlog

from app.core.database import Base, async_session_factory, engine
from app.core.security import hash_password
from app.models.db.interaction import (  # noqa: F401 — register tables
    SavedOpportunity,
    UserFeedback,
    UserInteraction,
)
from app.models.db.opportunity import Opportunity
from app.models.db.user import User, UserSkill

logger = structlog.get_logger(__name__)

SAMPLE_OPPORTUNITIES = [
    {
        "title": "PhD Position in Autonomous Agentic AI & Foundation Models",
        "opportunity_type": "PhD",
        "organization": "Stanford Artificial Intelligence Laboratory (SAIL)",
        "department": "Computer Science",
        "research_lab": "SAIL Lab",
        "professor": "Prof. Christopher Manning",
        "professor_email": "manning@cs.stanford.edu",
        "country": "United States",
        "city": "Stanford, CA",
        "location_type": "Onsite",
        "research_areas": ["Artificial Intelligence", "NLP", "Multi-Agent Systems", "LLMs"],
        "keywords": ["LangGraph", "Transformers", "Reasoning", "Reinforcement Learning"],
        "required_skills": ["Python", "PyTorch", "Deep Learning", "LLMs"],
        "programming_languages": ["Python", "C++"],
        "required_gpa": 3.7,
        "degree_levels": ["Master", "Bachelor"],
        "funding_type": "Fully Funded",
        "salary_range": "$52,000 / year + Full Tuition Waiver",
        "stipend": "$4,333 / month",
        "duration": "4-5 Years",
        "deadline": datetime.now(UTC) + timedelta(days=45),
        "application_link": "https://cs.stanford.edu/admissions/phd",
        "documents_required": [
            "CV",
            "Statement of Purpose",
            "3 Recommendation Letters",
            "Transcripts",
        ],
        "source_url": "https://cs.stanford.edu/jobs/phd-agentic-ai",
        "confidence_score": 0.98,
        "authenticity_score": 0.96,
        "summary": (
            "Full PhD position working on autonomous agent architectures, multi-agent "
            "coordination, and large language model reasoning."
        ),
    },
    {
        "title": "Postdoctoral Researcher in Graph Neural Networks & Knowledge Discovery",
        "opportunity_type": "Fellowship",
        "organization": "University of Oxford",
        "department": "Department of Computer Science",
        "research_lab": "Oxford Machine Learning Group",
        "professor": "Prof. Michael Bronstein",
        "country": "United Kingdom",
        "city": "Oxford",
        "location_type": "Hybrid",
        "research_areas": ["Graph Neural Networks", "Knowledge Graphs", "Geometric Deep Learning"],
        "keywords": ["Neo4j", "GraphML", "Representation Learning"],
        "required_skills": ["Python", "PyTorch Geometric", "Knowledge Graphs"],
        "programming_languages": ["Python"],
        "degree_levels": ["PhD"],
        "funding_type": "Fully Funded",
        "salary_range": "£42,000 - £48,000 per annum",
        "duration": "2 Years",
        "deadline": datetime.now(UTC) + timedelta(days=30),
        "application_link": "https://www.cs.ox.ac.uk/vacancies",
        "documents_required": ["CV", "Research Proposal", "2 Reference Letters"],
        "source_url": "https://www.cs.ox.ac.uk/jobs/postdoc-gnn-2026",
        "confidence_score": 0.95,
        "authenticity_score": 0.94,
        "summary": (
            "Research fellowship investigating geometric deep learning and large-scale "
            "knowledge graph representation learning."
        ),
    },
    {
        "title": "AI Research Scientist Intern (Summer 2026)",
        "opportunity_type": "Internship",
        "organization": "Google DeepMind",
        "department": "Generative AI Research",
        "country": "United Kingdom",
        "city": "London",
        "location_type": "Hybrid",
        "research_areas": ["Machine Learning", "Reinforcement Learning", "LLMs"],
        "keywords": ["Gemini", "Multimodal", "Scalable Training"],
        "required_skills": ["Python", "JAX", "TensorFlow", "Deep Learning"],
        "programming_languages": ["Python"],
        "degree_levels": ["Master", "PhD"],
        "funding_type": "Fully Funded",
        "salary_range": "Competitive Hourly Rate + Housing Allowance",
        "duration": "12 Weeks",
        "deadline": datetime.now(UTC) + timedelta(days=20),
        "application_link": "https://deepmind.google/careers/internships",
        "documents_required": ["CV", "Cover Letter", "Academic Transcript"],
        "source_url": "https://deepmind.google/jobs/internship-2026",
        "confidence_score": 0.99,
        "authenticity_score": 0.98,
        "summary": (
            "3-month summer research internship working alongside senior scientists on "
            "frontier multimodal foundation models."
        ),
    },
    {
        "title": "Graduate Fellowship in Quantum Machine Learning",
        "opportunity_type": "Fellowship",
        "organization": "ETH Zurich",
        "department": "Department of Physics & Computer Science",
        "professor": "Prof. Renato Renner",
        "country": "Switzerland",
        "city": "Zurich",
        "location_type": "Onsite",
        "research_areas": ["Quantum Computing", "Quantum Machine Learning", "Physics"],
        "keywords": ["Qiskit", "Quantum Algorithms", "Optimization"],
        "required_skills": ["Python", "Quantum Physics", "Linear Algebra"],
        "programming_languages": ["Python", "C++"],
        "degree_levels": ["Master"],
        "funding_type": "Fully Funded",
        "salary_range": "50,000 CHF / year",
        "duration": "3 Years",
        "deadline": datetime.now(UTC) + timedelta(days=60),
        "application_link": "https://ethz.ch/en/studies/phd",
        "documents_required": ["CV", "Transcripts", "Statement of Purpose"],
        "source_url": "https://ethz.ch/jobs/quantum-ml-fellowship",
        "confidence_score": 0.94,
        "authenticity_score": 0.95,
        "summary": (
            "Fully funded graduate fellowship focusing on quantum algorithms for "
            "machine learning applications."
        ),
    },
    {
        "title": "Research Assistantship in Computer Vision & Robotics",
        "opportunity_type": "Research Assistant",
        "organization": "Massachusetts Institute of Technology (MIT)",
        "department": "CSAIL",
        "professor": "Prof. Antonio Torralba",
        "country": "United States",
        "city": "Cambridge, MA",
        "location_type": "Onsite",
        "research_areas": ["Computer Vision", "Robotics", "Multimodal Learning"],
        "keywords": ["OpenCV", "PyTorch", "3D Vision", "NeRF"],
        "required_skills": ["Python", "PyTorch", "Computer Vision", "C++"],
        "programming_languages": ["Python", "C++"],
        "degree_levels": ["Bachelor", "Master"],
        "funding_type": "Fully Funded",
        "salary_range": "$48,000 / year + Benefits",
        "duration": "1-2 Years",
        "deadline": datetime.now(UTC) + timedelta(days=35),
        "application_link": "https://csail.mit.edu/careers",
        "documents_required": ["CV", "Portfolio", "2 Reference Letters"],
        "source_url": "https://csail.mit.edu/jobs/ra-vision-robotics",
        "confidence_score": 0.97,
        "authenticity_score": 0.97,
        "summary": (
            "Research assistant position exploring 3D scene representation, computer "
            "vision, and robotic manipulation at CSAIL."
        ),
    },
]


async def seed_database() -> None:
    """Create database tables and populate sample opportunities & test user."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        from sqlalchemy import delete, select

        # Reset opportunities to ensure clean array seeding
        await db.execute(delete(Opportunity))
        await db.commit()

        for opp_data in SAMPLE_OPPORTUNITIES:
            opp = Opportunity(id=uuid4(), **opp_data)
            db.add(opp)
        logger.info("opportunities_seeded", count=len(SAMPLE_OPPORTUNITIES))

        # Check demo user
        res_user = await db.execute(select(User).where(User.email == "demo@researchscout.ai"))
        demo_user = res_user.scalar_one_or_none()

        if not demo_user:
            demo_user = User(
                id=uuid4(),
                email="demo@researchscout.ai",
                password_hash=hash_password("demopassword123"),
                full_name="Alex Mercer",
                university="MIT",
                degree_level="Master",
                gpa=3.85,
                country="United States",
                preferred_countries=["United States", "United Kingdom", "Switzerland"],
                preferred_domains=["Artificial Intelligence", "Machine Learning", "NLP"],
                career_goals="Pursue a PhD in Autonomous Agent Architectures and LLMs.",
            )
            db.add(demo_user)
            await db.flush()

            # Add skills
            skills = ["Python", "PyTorch", "Deep Learning", "LLMs", "NLP"]
            for s in skills:
                db.add(
                    UserSkill(
                        id=uuid4(), user_id=demo_user.id, skill_name=s, proficiency="Advanced"
                    )
                )

            logger.info("demo_user_seeded", email=demo_user.email)

        await db.commit()
        print("Database successfully seeded with 5 rich opportunities and demo user!")


if __name__ == "__main__":
    asyncio.run(seed_database())
