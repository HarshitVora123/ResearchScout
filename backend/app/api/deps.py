"""API dependencies — auth, database sessions, and shared utilities."""

import hmac
from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models.db.user import User


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    access_token: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> User:
    """Extract and validate the current user from the JWT token."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    elif access_token:
        token = access_token
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(User)
        .where(User.id == UUID(user_id))
        .options(
            selectinload(User.skills),
            selectinload(User.publications),
            selectinload(User.projects),
            selectinload(User.research_interests),
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if payload.get("ver", 0) != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has been revoked"
        )

    return user


# Type alias for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def require_admin(
    user: CurrentUser,
    admin_key: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
) -> User:
    expected = get_settings().admin_api_key
    if not expected or not admin_key or not hmac.compare_digest(expected, admin_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required"
        )
    return user


AdminUser = Annotated[User, Depends(require_admin)]
