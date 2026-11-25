"""User profile endpoints — view, update, skills, publications, projects."""

import re
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.db.opportunity import Opportunity
from app.models.db.user import (
    User,
    UserProject,
    UserPublication,
    UserResearchInterest,
    UserSkill,
)
from app.models.schemas.common import MessageResponse
from app.models.schemas.user import (
    ProjectCreateRequest,
    PublicationCreateRequest,
    ResearchInterestCreateRequest,
    SkillCreateRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
)

router = APIRouter()


@router.get(
    "/profile",
    response_model=UserProfileResponse,
    summary="Get current user profile",
)
async def get_profile(user: CurrentUser, db: DbSession):
    """Get the current user's complete profile with skills, publications, and projects."""
    result = await db.execute(
        select(User)
        .where(User.id == user.id)
        .options(
            selectinload(User.skills),
            selectinload(User.publications),
            selectinload(User.projects),
            selectinload(User.research_interests),
        )
    )
    user_with_relations = result.scalar_one()
    return UserProfileResponse.model_validate(user_with_relations)


@router.put(
    "/profile",
    response_model=UserProfileResponse,
    summary="Update user profile",
)
async def update_profile(request: UserProfileUpdateRequest, user: CurrentUser, db: DbSession):
    """Update the current user's profile fields."""
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()

    # Reload with relations
    result = await db.execute(
        select(User)
        .where(User.id == user.id)
        .options(
            selectinload(User.skills),
            selectinload(User.publications),
            selectinload(User.projects),
            selectinload(User.research_interests),
        )
    )
    updated_user = result.scalar_one()
    return UserProfileResponse.model_validate(updated_user)


# ── Skills ───────────────────────────────────────────


@router.post(
    "/profile/skills",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a skill",
)
async def add_skill(request: SkillCreateRequest, user: CurrentUser, db: DbSession):
    """Add a skill to the current user's profile."""
    skill = UserSkill(
        user_id=user.id,
        skill_name=request.skill_name,
        proficiency=request.proficiency,
        years=request.years,
    )
    db.add(skill)
    return MessageResponse(message=f"Skill '{request.skill_name}' added successfully")


@router.delete(
    "/profile/skills/{skill_id}",
    response_model=MessageResponse,
    summary="Remove a skill",
)
async def remove_skill(skill_id: UUID, user: CurrentUser, db: DbSession):
    """Remove a skill from the current user's profile."""
    result = await db.execute(
        delete(UserSkill).where(UserSkill.id == skill_id, UserSkill.user_id == user.id)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Skill not found")
    return MessageResponse(message="Skill removed successfully")


# ── Publications ─────────────────────────────────────


@router.post(
    "/profile/publications",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a publication",
)
async def add_publication(request: PublicationCreateRequest, user: CurrentUser, db: DbSession):
    """Add a publication to the current user's profile."""
    pub = UserPublication(
        user_id=user.id,
        title=request.title,
        venue=request.venue,
        year=request.year,
        url=request.url,
        citation_count=request.citation_count,
    )
    db.add(pub)
    return MessageResponse(message=f"Publication '{request.title}' added successfully")


# ── Projects ─────────────────────────────────────────


@router.post(
    "/profile/projects",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a project",
)
async def add_project(request: ProjectCreateRequest, user: CurrentUser, db: DbSession):
    """Add a project to the current user's profile."""
    project = UserProject(
        user_id=user.id,
        title=request.title,
        description=request.description,
        technologies=request.technologies,
        url=request.url,
        start_date=request.start_date,
        end_date=request.end_date,
    )
    db.add(project)
    return MessageResponse(message=f"Project '{request.title}' added successfully")


# ── Research Interests ───────────────────────────────


@router.post(
    "/profile/research-interests",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a research interest",
)
async def add_research_interest(
    request: ResearchInterestCreateRequest, user: CurrentUser, db: DbSession
):
    """Add a research interest to the current user's profile."""
    interest = UserResearchInterest(
        user_id=user.id,
        topic=request.topic,
        weight=request.weight,
    )
    db.add(interest)
    return MessageResponse(message=f"Research interest '{request.topic}' added successfully")


@router.post(
    "/profile/resume",
    summary="Upload resume and get eligibility analysis",
)
async def upload_resume(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),  # noqa: B008
):
    """
    Upload a resume (PDF, DOCX, or TXT) for parsing, profile enrichment,
    and eligibility analysis against all active opportunities.

    Returns:
    - parsed_profile: everything extracted from the resume
    - profile_updates: what was added/changed on the user profile
    - matched_opportunities: all opportunities ranked by eligibility score
    """
    filename = file.filename or ""
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    if ext not in ["pdf", "docx", "txt"]:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOCX, and TXT files are supported.",
        )

    content_bytes = await file.read(10 * 1024 * 1024 + 1)
    if len(content_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Resume file must be 10 MiB or smaller")
    raw_text = ""

    if ext == "txt":
        raw_text = content_bytes.decode("utf-8", errors="ignore")
    elif ext == "pdf":
        try:
            import io

            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(content_bytes))
            if len(reader.pages) > 100:
                raise HTTPException(status_code=413, detail="Resume PDF cannot exceed 100 pages")
            raw_text = "\n".join((page.extract_text() or "") for page in reader.pages)[:100_000]
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail="The uploaded PDF could not be read",
            ) from exc
    elif ext == "docx":
        try:
            import io

            import docx

            doc = docx.Document(io.BytesIO(content_bytes))
            paragraph_text = [p.text for p in doc.paragraphs]
            table_text = [
                cell.text for table in doc.tables for row in table.rows for cell in row.cells
            ]
            raw_text = "\n".join(paragraph_text + table_text)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail="The uploaded DOCX could not be read",
            ) from exc

    if not raw_text.strip():
        raw_text = content_bytes.decode("utf-8", errors="ignore")

    # ── Parse resume ─────────────────────────────────
    from app.nlp.resume_parser import ResumeParser

    parser = ResumeParser()
    parsed = parser.parse_text(raw_text)

    # ── Track profile updates ────────────────────────
    profile_updates: dict[str, object] = {}

    replacing_malformed_education = bool(
        parsed.university
        and user.university
        and re.search(r"\b(?:c?gpa|gpa)\s*[:\-]", user.university, re.IGNORECASE)
    )
    if parsed.university and (not user.university or replacing_malformed_education):
        user.university = parsed.university
        profile_updates["university"] = parsed.university
    if parsed.degree_level and not user.degree_level:
        user.degree_level = parsed.degree_level
        profile_updates["degree_level"] = parsed.degree_level
    if parsed.gpa and (not user.gpa or replacing_malformed_education):
        user.gpa = parsed.gpa
        profile_updates["gpa"] = parsed.gpa

    # Save extracted projects and publications; the previous flow returned them
    # to the upload preview but never persisted them to the dashboard profile.
    existing_projects = {
        project.title.strip().casefold() for project in (user.projects or []) if project.title
    }
    projects_added: list[str] = []
    for project in parsed.projects:
        title = str(project.get("title", "")).strip()
        if not title or title.casefold() in existing_projects:
            continue
        db.add(
            UserProject(
                user_id=user.id,
                title=title,
                description=project.get("description"),
                technologies=project.get("technologies") or [],
            )
        )
        existing_projects.add(title.casefold())
        projects_added.append(title)

    existing_publications = {
        publication.title.strip().casefold()
        for publication in (user.publications or [])
        if publication.title
    }
    publications_added: list[str] = []
    for publication in parsed.publications:
        title = str(publication.get("title", "")).strip()
        if not title or title.casefold() in existing_publications:
            continue
        db.add(UserPublication(user_id=user.id, title=title))
        existing_publications.add(title.casefold())
        publications_added.append(title)

    # Add extracted skills (deduplicate)
    existing_skills = {s.skill_name.lower() for s in (user.skills or [])}
    new_skills: list[str] = []
    for skill_name in parsed.skills:
        if skill_name.lower() not in existing_skills:
            db.add(UserSkill(user_id=user.id, skill_name=skill_name, proficiency="Intermediate"))
            existing_skills.add(skill_name.lower())
            new_skills.append(skill_name)

    # Add extracted research interests (deduplicate)
    existing_interests = {i.topic.lower() for i in (user.research_interests or [])}
    new_interests: list[str] = []
    for topic in parsed.research_interests:
        if topic.lower() not in existing_interests:
            db.add(UserResearchInterest(user_id=user.id, topic=topic, weight=1.0))
            existing_interests.add(topic.lower())
            new_interests.append(topic)

    if new_skills:
        profile_updates["skills_added"] = new_skills
    if new_interests:
        profile_updates["research_interests_added"] = new_interests
    if projects_added:
        profile_updates["projects_added"] = projects_added
    if publications_added:
        profile_updates["publications_added"] = publications_added

    await db.commit()
    # CurrentUser eagerly loaded these collections before extraction. Refresh
    # them so the same request session (and immediate profile refresh) sees new rows.
    await db.refresh(
        user,
        attribute_names=["skills", "publications", "projects", "research_interests"],
    )

    # ── Build user profile dict for matching ─────────
    # Refresh skills/interests to include newly added ones
    all_user_skills = list(existing_skills)
    all_user_interests = list(existing_interests)

    user_profile = {
        "full_name": user.full_name,
        "degree_level": user.degree_level or parsed.degree_level,
        "university": user.university or parsed.university,
        "preferred_countries": user.preferred_countries or [],
        "skills": [{"skill_name": s} for s in all_user_skills],
        "research_interests": [{"topic": t} for t in all_user_interests],
    }

    # ── Match against all active opportunities ───────
    import json

    from app.nlp.skill_extraction import compute_skill_overlap
    from app.ranking.recommendation_engine import RecommendationEngine

    engine = RecommendationEngine()

    result = await db.execute(
        select(Opportunity)
        .where(Opportunity.is_active == True)  # noqa: E712
        .order_by(Opportunity.date_discovered.desc())
        .limit(100)
    )
    opportunities = result.scalars().all()

    matched_opportunities = []
    for opp in opportunities:
        # Normalize JSON list fields
        opp_research_areas = opp.research_areas or []
        opp_required_skills = opp.required_skills or []
        opp_prog_langs = opp.programming_languages or []
        opp_degree_levels = opp.degree_levels or []

        # Deserialize if stored as JSON strings (SQLite compat)
        for attr_name in (
            "research_areas",
            "required_skills",
            "programming_languages",
            "degree_levels",
        ):
            val = getattr(opp, attr_name, None)
            if isinstance(val, str):
                try:
                    val = json.loads(val)
                except Exception:
                    val = []
            if attr_name == "research_areas":
                opp_research_areas = val or []
            elif attr_name == "required_skills":
                opp_required_skills = val or []
            elif attr_name == "programming_languages":
                opp_prog_langs = val or []
            elif attr_name == "degree_levels":
                opp_degree_levels = val or []

        opp_data = {
            "title": opp.title,
            "organization": opp.organization,
            "opportunity_type": opp.opportunity_type,
            "country": opp.country,
            "research_areas": opp_research_areas,
            "required_skills": opp_required_skills,
            "programming_languages": opp_prog_langs,
            "degree_levels": opp_degree_levels,
            "confidence_score": opp.confidence_score,
            "deadline": opp.deadline.isoformat() if opp.deadline else None,
        }

        # Calculate eligibility
        rule_score, reasons = engine.calculate_rule_score(user_profile, opp_data)

        # Detailed skill overlap
        all_required = opp_required_skills + opp_prog_langs
        matched_skills, missing_skills, overlap_pct = compute_skill_overlap(
            all_required, all_user_skills
        )

        # Degree fit assessment
        user_deg = (user_profile.get("degree_level") or "").lower()
        degree_fit = "Unknown"
        if user_deg:
            opp_type = opp.opportunity_type or ""
            opp_degs_lower = [d.lower() for d in opp_degree_levels]
            if user_deg in opp_degs_lower or (
                ("phd" in user_deg and opp_type in ("Postdoc", "AI Residency"))
                or (
                    "master" in user_deg
                    and opp_type in ("PhD", "Research Assistant", "AI Residency")
                )
                or (
                    "bachelor" in user_deg
                    and opp_type in ("Internship", "Scholarship", "PhD", "Master")
                )
            ):
                degree_fit = "Eligible"
            elif opp_degs_lower:
                degree_fit = "May not match"
            else:
                degree_fit = "No requirement listed"
        else:
            degree_fit = "Degree not detected"

        # Research alignment
        user_areas = {t.lower() for t in all_user_interests}
        opp_areas_lower = {a.lower() for a in opp_research_areas}
        aligned_areas = []
        for ua in user_areas:
            for oa in opp_areas_lower:
                if ua in oa or oa in ua:
                    aligned_areas.append(oa.title())

        # Composite eligibility score (0-100)
        eligibility_score = int(round(rule_score * 100))

        matched_opportunities.append(
            {
                "opportunity_id": str(opp.id),
                "opportunity": {
                    "title": opp.title,
                    "organization": opp.organization,
                    "opportunity_type": opp.opportunity_type,
                    "country": opp.country,
                    "city": opp.city,
                    "research_areas": opp_research_areas,
                    "required_skills": opp_required_skills,
                    "funding_type": opp.funding_type,
                    "deadline": opp.deadline.isoformat() if opp.deadline else None,
                    "summary": opp.summary,
                    "application_link": opp.application_link,
                },
                "eligibility_score": eligibility_score,
                "skill_match": {
                    "matched": matched_skills,
                    "missing": missing_skills,
                    "overlap_pct": int(round(overlap_pct * 100)),
                },
                "degree_fit": degree_fit,
                "research_alignment": sorted(set(aligned_areas)),
                "match_reasons": reasons,
            }
        )

    # Sort by eligibility score descending
    matched_opportunities.sort(key=lambda x: x["eligibility_score"], reverse=True)

    return {
        "parsed_profile": {
            "full_name": parsed.full_name,
            "email": parsed.email,
            "university": parsed.university,
            "degree_level": parsed.degree_level,
            "major": parsed.major,
            "gpa": parsed.gpa,
            "experience_years": parsed.experience_years,
            "skills": parsed.skills,
            "programming_languages": parsed.programming_languages,
            "research_interests": parsed.research_interests,
            "publications": parsed.publications,
            "projects": parsed.projects,
        },
        "profile_updates": profile_updates,
        "matched_opportunities": matched_opportunities,
    }
