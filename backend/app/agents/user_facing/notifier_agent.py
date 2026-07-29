"""
Notifier Agent — dispatches notifications across Email (SendGrid), Telegram, and Discord.

Handles:
- Immediate alerts for top matching opportunities
- Daily digest emails
- Deadline warning alerts (e.g. deadline in 7 days / 3 days)
"""

from typing import Any

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class NotifierAgent:
    """
    Multi-channel Notification Agent.
    """

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
    ) -> bool:
        """Send an email notification via SendGrid API or mock fallback."""
        if not settings.sendgrid_api_key:
            logger.info("email_mock_sent", to=to_email, subject=subject)
            return True

        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {settings.sendgrid_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": settings.sendgrid_from_email},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_content}],
        }

        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(url, json=payload, headers=headers)
            if res.status_code in (200, 202):
                logger.info("email_sent", to=to_email, subject=subject)
                return True
            else:
                logger.warning("email_send_failed", status=res.status_code)
                return False

    async def send_telegram(
        self,
        chat_id: str,
        message_markdown: str,
    ) -> bool:
        """Send a message via Telegram Bot API."""
        if not settings.telegram_bot_token:
            logger.info("telegram_mock_sent", chat_id=chat_id)
            return True

        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message_markdown,
            "parse_mode": "Markdown",
        }

        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(url, json=payload)
            return res.status_code == 200

    async def send_discord(
        self,
        webhook_url: str | None,
        title: str,
        description: str,
        fields: list[dict] | None = None,
    ) -> bool:
        """Send a rich embed message via Discord Webhook."""
        url = webhook_url or settings.discord_webhook_url
        if not url:
            logger.info("discord_mock_sent", title=title)
            return True

        payload = {
            "embeds": [
                {
                    "title": title,
                    "description": description,
                    "color": 5814783,  # Indigo accent color
                    "fields": fields or [],
                    "footer": {"text": "ResearchScout AI Agent Platform"},
                }
            ]
        }

        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(url, json=payload)
            return res.status_code in (200, 204)

    def generate_daily_digest_html(
        self,
        user_name: str,
        recommendations: list[dict[str, Any]],
    ) -> str:
        """Format top recommendations into an HTML daily digest email."""
        items_html = ""
        for item in recommendations[:5]:
            opp = item.get("opportunity", {})
            reasons = "<br>• ".join(item.get("match_reasons", []))

            items_html += f"""
            <div style="margin-bottom: 20px; padding: 16px; border: 1px solid #e2e8f0; border-radius: 8px;">
                <h3 style="margin: 0 0 8px 0; color: #1e293b;">{opp.get('title', 'Opportunity')}</h3>
                <p style="margin: 0 0 8px 0; font-weight: 600; color: #475569;">🏛️ {opp.get('organization', '')} • 📍 {opp.get('country', 'Worldwide')}</p>
                <div style="background: #f8fafc; padding: 10px; border-radius: 6px; font-size: 13px; color: #334155;">
                    <strong>Why this matches:</strong><br>• {reasons}
                </div>
            </div>
            """

        return f"""
        <html>
            <body style="font-family: system-ui, sans-serif; line-height: 1.5; color: #0f172a; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #6366f1;">🔬 ResearchScout Daily Digest</h2>
                <p>Hello {user_name},</p>
                <p>Here are your top personalized research opportunity recommendations for today:</p>
                {items_html}
                <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0;">
                <p style="font-size: 12px; color: #94a3b8; text-align: center;">
                    ResearchScout • Autonomous AI Research Discovery Platform
                </p>
            </body>
        </html>
        """
