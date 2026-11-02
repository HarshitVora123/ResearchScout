"""Notification settings and dispatch endpoints."""

from fastapi import APIRouter
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import select

from app.agents.user_facing.notifier_agent import NotifierAgent
from app.api.deps import CurrentUser, DbSession
from app.models.db.notification import NotificationPreference

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
    channel: Literal["email", "telegram", "discord"]


@router.get("/settings")
async def get_notification_settings(user: CurrentUser, db: DbSession):
    """Get current user notification preferences."""
    result = await db.execute(select(NotificationPreference).where(NotificationPreference.user_id == user.id))
    saved = {p.channel: p for p in result.scalars().all()}
    return {
        "user_id": str(user.id),
        "email": user.email,
        "email_enabled": saved.get("email", None).enabled if saved.get("email") else True,
        "telegram_enabled": saved.get("telegram", None).enabled if saved.get("telegram") else False,
        "discord_enabled": saved.get("discord", None).enabled if saved.get("discord") else False,
        "daily_digest": saved.get("digest", None).enabled if saved.get("digest") else True,
        "deadline_reminders": saved.get("deadlines", None).enabled if saved.get("deadlines") else True,
    }


@router.put("/settings")
async def update_notification_settings(req: NotificationSettingsRequest, user: CurrentUser, db: DbSession):
    values = {
        "email": (req.email_enabled, {}),
        "telegram": (req.telegram_enabled, {"chat_id": req.telegram_chat_id} if req.telegram_chat_id else {}),
        "discord": (req.discord_enabled, {"webhook_url": req.discord_webhook_url} if req.discord_webhook_url else {}),
        "digest": (req.daily_digest, {}),
        "deadlines": (req.deadline_reminders, {}),
    }
    result = await db.execute(select(NotificationPreference).where(NotificationPreference.user_id == user.id))
    existing = {p.channel: p for p in result.scalars().all()}
    for channel, (enabled, config) in values.items():
        preference = existing.get(channel)
        if preference:
            preference.enabled = enabled
            if config:
                preference.config = config
        else:
            db.add(NotificationPreference(user_id=user.id, channel=channel, enabled=enabled, config=config))
    return {"message": "Notification settings saved"}


@router.post("/test")
async def send_test_notification(req: TestNotificationRequest, user: CurrentUser, db: DbSession):
    """Send a test notification via selected channel."""
    notifier = NotifierAgent()
    success = False

    if req.channel == "email":
        result = await db.execute(select(NotificationPreference).where(NotificationPreference.user_id == user.id, NotificationPreference.channel == "email"))
        preference = result.scalar_one_or_none()
        success = (preference is None or preference.enabled) and await notifier.send_email(
            to_email=user.email,
            subject="ResearchScout Test Notification",
            html_content="<p>This is a test notification from ResearchScout!</p>",
        )
    elif req.channel == "telegram":
        result = await db.execute(select(NotificationPreference).where(NotificationPreference.user_id == user.id, NotificationPreference.channel == "telegram"))
        preference = result.scalar_one_or_none()
        success = bool(preference and preference.enabled and preference.config and preference.config.get("chat_id")) and await notifier.send_telegram(
            chat_id=preference.config["chat_id"],
            message_markdown="🔬 *ResearchScout Test Notification*",
        )
    elif req.channel == "discord":
        result = await db.execute(select(NotificationPreference).where(NotificationPreference.user_id == user.id, NotificationPreference.channel == "discord"))
        preference = result.scalar_one_or_none()
        success = bool(preference and preference.enabled and preference.config and preference.config.get("webhook_url")) and await notifier.send_discord(
            webhook_url=preference.config.get("webhook_url") if preference and preference.config else None,
            title="ResearchScout Test Notification",
            description="Discord webhook notification test.",
        )

    return {
        "channel": req.channel,
        "status": "sent" if success else "not_configured_or_failed",
    }
