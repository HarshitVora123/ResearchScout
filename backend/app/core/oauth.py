"""
OAuth2 Integration Module — Google and GitHub Social Authentication.
"""

from typing import Any

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class OAuth2Service:
    """OAuth2 integration service for Google & GitHub logins."""

    async def verify_google_token(self, id_token_str: str) -> dict[str, Any] | None:
        """Verify Google OAuth2 ID token and extract user info."""
        url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token_str}"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    return {
                        "email": data.get("email"),
                        "full_name": data.get("name", data.get("email")),
                        "google_id": data.get("sub"),
                    }
        except Exception as e:
            logger.warning("google_oauth_verify_failed", error=str(e))
        return None

    async def verify_github_token(self, access_token: str) -> dict[str, Any] | None:
        """Verify GitHub OAuth2 access token and fetch user profile."""
        url = "https://api.github.com/user"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": settings.app_name,
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    return {
                        "email": data.get("email") or f"{data.get('login')}@users.noreply.github.com",
                        "full_name": data.get("name") or data.get("login"),
                        "github_id": str(data.get("id")),
                    }
        except Exception as e:
            logger.warning("github_oauth_verify_failed", error=str(e))
        return None
