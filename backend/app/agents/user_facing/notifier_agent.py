"""
Notifier Agent — dispatches notifications across Email (SendGrid), Telegram, and Discord.

Handles:
- Immediate alerts for top matching opportunities
- Daily digest emails
- Deadline warning alerts (e.g. deadline in 7 days / 3 days)
"""

from typing import Any
from html import escape

import httpx
import structlog
from urllib.parse import urlparse

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
            logger.warning("email_not_sent_missing_sendgrid_key", to=to_email)
            return False

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

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.post(url, json=payload, headers=headers)
            if res.status_code in (200, 202):
                logger.info("email_sent", to=to_email, subject=subject)
                return True
            logger.warning("email_send_failed", status=res.status_code)
        except httpx.HTTPError as exc:
            logger.warning("email_send_failed", error=str(exc))
        return False

    async def send_telegram(
        self,
        chat_id: str,
        message_markdown: str,
    ) -> bool:
        """Send a message via Telegram Bot API."""
        if not settings.telegram_bot_token:
            logger.warning("telegram_not_sent_missing_bot_token")
            return False

        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message_markdown,
            "parse_mode": "Markdown",
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.post(url, json=payload)
            return res.status_code == 200
        except httpx.HTTPError as exc:
            logger.warning("telegram_send_failed", error=str(exc))
            return False

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
            logger.warning("discord_not_sent_missing_webhook")
            return False
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in {"discord.com", "discordapp.com"} or not parsed.path.startswith("/api/webhooks/"):
            logger.warning("discord_webhook_rejected")
            return False

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

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.post(url, json=payload)
            return res.status_code in (200, 204)
        except httpx.HTTPError as exc:
            logger.warning("discord_send_failed", error=str(exc))
            return False

    def generate_daily_digest_html(
        self,
        user_name: str,
        recommendations: list[dict[str, Any]],
    ) -> str:
        """Format top recommendations into an HTML daily digest email."""
        items_html = ""
        for item in recommendations[:5]:
            opp = item.get("opportunity", {})
            reasons = "<br>• ".join(escape(str(reason)) for reason in item.get("match_reasons", []))

            items_html += f"""
            <div style="margin-bottom: 20px; padding: 16px; border: 1px solid #e2e8f0; border-radius: 8px;">
                <h3 style="margin: 0 0 8px 0; color: #1e293b;">{escape(str(opp.get('title', 'Opportunity')))}</h3>
                <p style="margin: 0 0 8px 0; font-weight: 600; color: #475569;">🏛️ {escape(str(opp.get('organization', '')))} • 📍 {escape(str(opp.get('country', 'Worldwide')))}</p>
                {f"<p>Deadline: {escape(str(opp.get('deadline')))}</p>" if opp.get('deadline') else ""}
                <div style="background: #f8fafc; padding: 10px; border-radius: 6px; font-size: 13px; color: #334155;">
                    <strong>Why this matches:</strong><br>• {reasons}
                </div>
            </div>
            """

        return f"""
        <html>
            <body style="font-family: system-ui, sans-serif; line-height: 1.5; color: #0f172a; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #6366f1;">🔬 ResearchScout Daily Digest</h2>
                <p>Hello {escape(user_name)},</p>
                <p>Here are your top personalized research opportunity recommendations for today:</p>
                {items_html}
                <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0;">
                <p style="font-size: 12px; color: #94a3b8; text-align: center;">
                    ResearchScout • Autonomous AI Research Discovery Platform
                </p>
            </body>
        </html>
        """
