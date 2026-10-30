"""
Outgoing email via a real SMTP server configured through environment variables.

Nothing is "simulated": if SMTP_HOST / SMTP_FROM are not configured, `settings.email_configured` is False
and the features that need email (password recovery) report that they are unavailable instead of
pretending a message was sent.
"""

import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("travelsync.email")


class EmailDeliveryError(Exception):
    pass


def _send_sync(to_address: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
            if settings.smtp_starttls:
                client.starttls(context=ssl.create_default_context())
            if settings.smtp_username:
                client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailDeliveryError(type(exc).__name__) from exc


async def send_email(to_address: str, subject: str, body: str) -> None:
    if not settings.email_configured:
        raise EmailDeliveryError("email is not configured")
    await asyncio.to_thread(_send_sync, to_address, subject, body)
