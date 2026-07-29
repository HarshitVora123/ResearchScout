"""SQLAlchemy ORM model for notification preferences."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class NotificationPreference(Base):
    """User notification channel preferences."""

    __tablename__ = "notification_preferences"
    __table_args__ = (UniqueConstraint("user_id", "channel"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # email, telegram, discord, slack, push
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    frequency: Mapped[str] = mapped_column(
        String(20), default="daily"
    )  # instant, daily, weekly
    config: Mapped[dict | None] = mapped_column(
        JSONB
    )  # Channel-specific config (chat_id, webhook_url, etc.)

    def __repr__(self) -> str:
        return f"<NotificationPreference {self.channel!r} enabled={self.enabled}>"
