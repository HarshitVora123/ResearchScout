"""Authentication endpoints — register, login, refresh tokens."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.config import get_settings
from app.models.db.user import User
from app.models.schemas.user import (
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)
from app.models.schemas.common import MessageResponse

router = APIRouter()
settings = get_settings()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(request: UserRegisterRequest, db: DbSession):
    """Register a new user account and return JWT tokens."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create user
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        full_name=request.full_name,
    )
    db.add(user)
    await db.flush()  # Get the generated ID

    # Generate tokens
    token_data = {"sub": str(user.id)}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
)
async def login(request: UserLoginRequest, db: DbSession):
    """Authenticate user and return JWT tokens."""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token_data = {"sub": str(user.id)}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh an access token",
)
async def refresh_token(request: RefreshTokenRequest, db: DbSession):
    """Exchange a refresh token for a new access token."""
    payload = decode_token(request.refresh_token)

    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    token_data = {"sub": user_id}
    access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


class OAuthLoginRequest(BaseModel):
    token: str
    provider: str  # "google" or "github"


@router.post(
    "/oauth",
    response_model=TokenResponse,
    summary="Login or register via OAuth2 (Google/GitHub)",
)
async def oauth_login(request: OAuthLoginRequest, db: DbSession):
    """Authenticate or register user via Google or GitHub OAuth2."""
    from app.core.oauth import OAuth2Service

    oauth_service = OAuth2Service()
    profile = None

    if request.provider == "google":
        profile = await oauth_service.verify_google_token(request.token)
    elif request.provider == "github":
        profile = await oauth_service.verify_github_token(request.token)

    if not profile or not profile.get("email"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid {request.provider} OAuth token",
        )

    # Find existing user by email
    result = await db.execute(select(User).where(User.email == profile["email"]))
    user = result.scalar_one_or_none()

    if not user:
        # Create new user via OAuth
        user = User(
            email=profile["email"],
            password_hash=hash_password(f"oauth_{request.provider}_{profile['email']}"),
            full_name=profile["full_name"],
        )
        db.add(user)
        await db.flush()

    token_data = {"sub": str(user.id)}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )

