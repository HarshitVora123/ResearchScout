"""User profile endpoints — view, update, skills, publications, projects."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, File, status
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.db.user import (
    User,
    UserProject,
    UserPublication,
    UserResearchInterest,
    UserSkill,
)
from app.models.schemas.user import (
    ProjectCreateRequest,
    PublicationCreateRequest,
    ResearchInterestCreateRequest,
    SkillCreateRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
)
from app.models.schemas.common import MessageResponse

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
async def update_profile(
    request: UserProfileUpdateRequest, user: CurrentUser, db: DbSession
):
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
        delete(UserSkill).where(
            UserSkill.id == skill_id, UserSkill.user_id == user.id
        )
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
async def add_publication(
    request: PublicationCreateRequest, user: CurrentUser, db: DbSession
):
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
async def add_project(
    request: ProjectCreateRequest, user: CurrentUser, db: DbSession
):
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
    response_model=MessageResponse,
    summary="Upload resume",
)
async def upload_resume(
    file: UploadFile = File(...),
    user: CurrentUser = None,
    db: DbSession = None,
):
    """Upload a resume (PDF or DOCX) for parsing and profile enrichment."""
    if file.content_type not in [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are accepted",
        )

    # TODO: Save to MinIO and trigger LLM resume parsing
    return MessageResponse(message="Resume uploaded successfully. Parsing will begin shortly.")
