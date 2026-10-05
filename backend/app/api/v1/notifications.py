"""Notification settings and dispatch endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.user_facing.notifier_agent import NotifierAgent
from app.api.deps import CurrentUser

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationSettingsRequest(BaseModel):
    email_enabled: bool = True
    telegram_enabled: bool = False
    telegram_chat_id: str | None = None
    discord_enabled: bool = False
    discord_webhook_url: str | None = None
    daily_digest: bool = True
    deadline_reminders: bool = True


class TestNotificationRequest(BaseModel):
    channel: str  # "email", "telegram", "discord"


@router.get("/settings")
async def get_notification_settings(user: CurrentUser):
    """Get current user notification preferences."""
    return {
        "user_id": str(user.id),
        "email": user.email,
        "email_enabled": True,
        "telegram_enabled": False,
        "discord_enabled": False,
        "daily_digest": True,
        "deadline_reminders": True,
    }


@router.post("/test")
async def send_test_notification(req: TestNotificationRequest, user: CurrentUser):
    """Send a test notification via selected channel."""
    notifier = NotifierAgent()
    success = False

    if req.channel == "email":
        success = await notifier.send_email(
            to_email=user.email,
            subject="ResearchScout Test Notification",
            html_content="<p>This is a test notification from ResearchScout!</p>",
        )
    elif req.channel == "telegram":
        success = await notifier.send_telegram(
            chat_id="test_chat",
            message_markdown="🔬 *ResearchScout Test Notification*",
        )
    elif req.channel == "discord":
        success = await notifier.send_discord(
            webhook_url=None,
            title="ResearchScout Test Notification",
            description="Discord webhook notification test.",
        )

    return {
        "channel": req.channel,
        "status": "sent" if success else "failed",
    }
