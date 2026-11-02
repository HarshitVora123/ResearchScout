"""Notification worker — background tasks for sending notifications."""

from datetime import UTC, datetime, timedelta

from app.workers.celery_app import celery_app


@celery_app.task(
    name="app.workers.notification_worker.send_email",
    bind=True,
    queue="default",
    max_retries=5,
    default_retry_delay=30,
)
def send_email(self, to_email: str, subject: str, body: str):
    """
    Send an email notification via SendGrid with bounded Celery retries.
    """
    import asyncio

    from app.agents.user_facing.notifier_agent import NotifierAgent

    try:
        sent = asyncio.run(NotifierAgent().send_email(to_email, subject, body))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
    if not sent:
        raise self.retry(exc=RuntimeError("Email delivery failed"), countdown=30)
    return {"to": to_email, "subject": subject, "status": "sent" if sent else "failed"}


@celery_app.task(
    name="app.workers.notification_worker.send_telegram",
    bind=True,
    max_retries=5,
    default_retry_delay=30,
    queue="default",
)
def send_telegram(self, chat_id: str, message: str):
    """Send a Telegram notification."""
    import asyncio

    from app.agents.user_facing.notifier_agent import NotifierAgent

    try:
        sent = asyncio.run(NotifierAgent().send_telegram(chat_id, message))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
    if not sent:
        raise self.retry(exc=RuntimeError("Telegram delivery failed"), countdown=30)
    return {"chat_id": chat_id, "status": "sent" if sent else "failed"}


@celery_app.task(
    name="app.workers.notification_worker.send_daily_digest",
    queue="default",
)
def send_daily_digest():
    """
    Generate and send daily digest to all users with daily notification preference.

    Called daily by Celery Beat.
    """
    import asyncio

    return asyncio.run(_send_daily_digest())


async def _send_daily_digest() -> dict:
    from sqlalchemy import and_, or_, select
    from sqlalchemy.orm import aliased

    from app.agents.user_facing.notifier_agent import NotifierAgent
    from app.core.database import async_session_factory
    from app.models.db.notification import NotificationPreference
    from app.models.db.opportunity import Opportunity
    from app.models.db.user import User

    cutoff = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    async with async_session_factory() as db:
        email_pref = aliased(NotificationPreference)
        digest_pref = aliased(NotificationPreference)
        users_result = await db.execute(
            select(User)
            .outerjoin(
                email_pref,
                and_(email_pref.user_id == User.id, email_pref.channel == "email"),
            )
            .outerjoin(
                digest_pref,
                and_(digest_pref.user_id == User.id, digest_pref.channel == "digest"),
            )
            .where(
                or_(email_pref.id.is_(None), email_pref.enabled.is_(True)),
                or_(digest_pref.id.is_(None), digest_pref.enabled.is_(True)),
            )
        )
        users = users_result.scalars().unique().all()
        opp_result = await db.execute(
            select(Opportunity).where(Opportunity.is_active.is_(True), Opportunity.date_discovered >= cutoff)
            .order_by(Opportunity.confidence_score.desc()).limit(20)
        )
        opportunities = opp_result.scalars().all()

    notifier = NotifierAgent()
    sent = 0
    failed = 0
    for user in users:
        html = notifier.generate_daily_digest_html(user.full_name, [
            {"opportunity": {"title": o.title, "organization": o.organization, "country": o.country}}
            for o in opportunities
        ])
        if await notifier.send_email(user.email, "Your ResearchScout daily digest", html):
            sent += 1
        else:
            failed += 1
    return {"status": "complete", "sent": sent, "failed": failed, "timestamp": datetime.now(UTC).isoformat()}


@celery_app.task(name="app.workers.notification_worker.send_deadline_reminders", queue="default")
def send_deadline_reminders():
    import asyncio

    return asyncio.run(_send_deadline_reminders())


async def _send_deadline_reminders() -> dict:
    from sqlalchemy import and_, or_, select
    from sqlalchemy.orm import aliased

    from app.agents.user_facing.notifier_agent import NotifierAgent
    from app.core.database import async_session_factory
    from app.models.db.notification import NotificationPreference
    from app.models.db.opportunity import Opportunity
    from app.models.db.user import User

    now = datetime.now(UTC)
    cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
    async with async_session_factory() as db:
        email_pref = aliased(NotificationPreference)
        deadline_pref = aliased(NotificationPreference)
        result = await db.execute(
            select(User)
            .outerjoin(
                email_pref,
                and_(email_pref.user_id == User.id, email_pref.channel == "email"),
            )
            .outerjoin(
                deadline_pref,
                and_(deadline_pref.user_id == User.id, deadline_pref.channel == "deadlines"),
            )
            .where(
                or_(email_pref.id.is_(None), email_pref.enabled.is_(True)),
                or_(deadline_pref.id.is_(None), deadline_pref.enabled.is_(True)),
            )
        )
        users = result.scalars().unique().all()
        opp_result = await db.execute(
            select(Opportunity)
            .where(Opportunity.is_active.is_(True), Opportunity.deadline >= cutoff,
                   Opportunity.deadline <= now + timedelta(days=7))
            .order_by(Opportunity.deadline.asc()).limit(100)
        )
        opportunities = opp_result.scalars().all()

    notifier = NotifierAgent()
    sent = failed = 0
    for user in users:
        html = notifier.generate_daily_digest_html(user.full_name, [
            {"opportunity": {"title": o.title, "organization": o.organization,
                             "country": o.country, "deadline": o.deadline.isoformat() if o.deadline else ""}}
            for o in opportunities
        ])
        delivered = await notifier.send_email(user.email, "ResearchScout: upcoming application deadlines", html)
        sent += int(delivered)
        failed += int(not delivered)
    return {"status": "complete", "sent": sent, "failed": failed, "timestamp": datetime.now(UTC).isoformat()}
