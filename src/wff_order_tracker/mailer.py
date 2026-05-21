"""Email delivery helper for generated fulfillment reports."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

from .config import Settings


def send_report(settings: Settings, report_path: Path, subject: str, body: str) -> None:
    """Send the generated report by SMTP.

    When DRY_RUN=true or SMTP settings are incomplete, the function logs the
    intended action and exits without sending mail.
    """

    recipients = [item.strip() for item in settings.mail_to.split(",") if item.strip()]
    if settings.dry_run or not settings.smtp_host or not settings.mail_from or not recipients:
        print(f"[DRY-RUN] Would send {report_path} to {recipients or '[MAIL_TO not configured]'}")
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.mail_from
    message["To"] = ", ".join(recipients)
    message.set_content(body)
    message.add_attachment(
        report_path.read_bytes(),
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=report_path.name,
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
