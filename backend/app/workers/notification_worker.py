"""Notification worker — background tasks for sending notifications."""

from datetime import UTC, datetime

from app.workers.celery_app import celery_app


@celery_app.task(
    name="app.workers.notification_worker.send_email",
    queue="default",
    max_retries=5,
    default_retry_delay=30,
)
def send_email(to_email: str, subject: str, body: str):
    """
    Send an email notification via SendGrid.

    Placeholder — will be implemented with the Notifier Agent in Phase 4.
    """
    # TODO: Implement SendGrid integration
    return {"to": to_email, "subject": subject, "status": "sent"}


@celery_app.task(
    name="app.workers.notification_worker.send_telegram",
    queue="default",
)
def send_telegram(chat_id: str, message: str):
    """Send a Telegram notification."""
    # TODO: Implement Telegram Bot API integration
    return {"chat_id": chat_id, "status": "sent"}


@celery_app.task(
    name="app.workers.notification_worker.send_daily_digest",
    queue="default",
)
def send_daily_digest():
    """
    Generate and send daily digest to all users with daily notification preference.

    Called daily by Celery Beat.
    """
    # TODO:
    # 1. Query users with daily digest enabled
    # 2. For each user, get new recommendations since last digest
    # 3. Generate digest content
    # 4. Send via preferred channel
    return {"status": "digest_sent", "timestamp": datetime.now(UTC).isoformat()}
