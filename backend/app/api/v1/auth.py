"""Authentication endpoints — register, login, refresh tokens."""

from secrets import token_urlsafe
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.config import get_settings
from app.core.auth_throttle import (
    MAX_FAILED_LOGINS,
    MAX_REGISTRATIONS,
    check_auth_rate,
    clear_auth_rate,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.db.user import User
from app.models.schemas.common import MessageResponse
from app.models.schemas.user import (
    RefreshTokenRequest,
    UserLoginRequest,
    UserRegisterRequest,
)

router = APIRouter()
settings = get_settings()


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        path="/",
    )


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    request: UserRegisterRequest, db: DbSession, response: Response, http_request: Request
):
    """Register a new user account and return JWT tokens."""
    client_ip = http_request.client.host if http_request.client else "unknown"
    if not await check_auth_rate(f"register:{client_ip}", MAX_REGISTRATIONS):
        raise HTTPException(
            status_code=429, detail="Too many registration attempts. Try again later."
        )
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
    try:
        await db.flush()  # Get the generated ID
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        ) from exc

    # Persist the user before returning a cookie that depends on that user ID.
    await db.commit()

    # Generate tokens
    token_data = {"sub": str(user.id), "ver": user.token_version}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    _set_auth_cookies(response, access_token, refresh_token)
    return MessageResponse(message="Registration successful")


@router.post(
    "/login",
    response_model=MessageResponse,
    summary="Login with email and password",
)
async def login(
    request: UserLoginRequest, db: DbSession, response: Response, http_request: Request
):
    """Authenticate user and return JWT tokens."""
    client_ip = http_request.client.host if http_request.client else "unknown"
    throttle_key = f"login:{client_ip}:{request.email.casefold()}"
    if not await check_auth_rate(throttle_key, MAX_FAILED_LOGINS):
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    await clear_auth_rate(throttle_key)

    token_data = {"sub": str(user.id), "ver": user.token_version}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    _set_auth_cookies(response, access_token, refresh_token)
    return MessageResponse(message="Login successful")


@router.post(
    "/refresh",
    response_model=MessageResponse,
    summary="Refresh an access token",
)
async def refresh_token(
    http_request: Request,
    response: Response,
    db: DbSession,
    request: RefreshTokenRequest | None = None,
):
    """Exchange a refresh token for a new access token."""
    token = (request.refresh_token if request else None) or http_request.cookies.get(
        "refresh_token"
    )
    payload = decode_token(token) if token else None

    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or payload.get("ver", 0) != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    current_version = user.token_version
    next_version = current_version + 1
    updated = await db.execute(
        update(User)
        .where(User.id == user.id, User.token_version == current_version)
        .values(token_version=User.token_version + 1)
    )
    if updated.rowcount != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token was already used"
        )
    await db.commit()
    token_data = {"sub": user_id, "ver": next_version}
    access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    _set_auth_cookies(response, access_token, new_refresh_token)
    return MessageResponse(message="Session refreshed")


@router.get("/session")
async def session(user: CurrentUser):
    return {"authenticated": True}


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response, user: CurrentUser, db: DbSession):
    user.token_version += 1
    await db.commit()
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return MessageResponse(message="Logged out")


class OAuthLoginRequest(BaseModel):
    token: str
    provider: Literal["google", "github"]


@router.post(
    "/oauth",
    response_model=MessageResponse,
    summary="Login or register via OAuth2 (Google/GitHub)",
)
async def oauth_login(request: OAuthLoginRequest, db: DbSession, response: Response):
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
            password_hash=hash_password(token_urlsafe(32)),
            full_name=profile["full_name"],
        )
        db.add(user)
        await db.flush()

    # New OAuth accounts must exist before their session cookie can be used.
    await db.commit()

    token_data = {"sub": str(user.id), "ver": user.token_version}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    _set_auth_cookies(response, access_token, refresh_token)
    return MessageResponse(message="Login successful")
