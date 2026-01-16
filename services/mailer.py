from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import get_settings


def send_email(to_email: str, subject: str, body: str) -> None:
    """Send an email via SMTP.

    For development, you can use MailHog (docker-compose) on localhost:1025.
    """
    settings = get_settings()

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg.set_content(body)

    if settings.smtp_use_tls:
        server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port)
    else:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)

    try:
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass
