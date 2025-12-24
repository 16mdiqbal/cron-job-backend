"""
Email notification helpers (FastAPI/Flask-free).

Historically this project used Flask-Mail and `current_app`. After the FastAPI cutover,
we send notifications directly via SMTP so scheduler jobs don't require any Flask app context.
"""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Iterable, Optional, Sequence

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if raw in {"true", "1", "yes", "y"}:
        return True
    if raw in {"false", "0", "no", "n"}:
        return False
    return default


def _smtp_host() -> str:
    return (os.getenv("SMTP_HOST") or os.getenv("MAIL_SERVER") or "").strip()


def _smtp_port() -> int:
    raw = (os.getenv("SMTP_PORT") or os.getenv("MAIL_PORT") or "").strip()
    try:
        return int(raw)
    except Exception:
        return 587


def _smtp_username() -> str:
    return (os.getenv("SMTP_USERNAME") or os.getenv("MAIL_USERNAME") or "").strip()


def _smtp_password() -> str:
    return (os.getenv("SMTP_PASSWORD") or os.getenv("MAIL_PASSWORD") or "").strip()


def _smtp_use_tls() -> bool:
    # STARTTLS by default.
    return _env_bool("SMTP_USE_TLS", _env_bool("MAIL_USE_TLS", True))


def _mail_enabled() -> bool:
    return _env_bool("MAIL_ENABLED", True)


def _from_address() -> str:
    return (os.getenv("MAIL_FROM") or os.getenv("MAIL_DEFAULT_SENDER") or _smtp_username() or "").strip()


def _normalize_recipients(recipient_emails: Sequence[str] | str | None) -> list[str]:
    if not recipient_emails:
        return []
    if isinstance(recipient_emails, str):
        emails: Iterable[str] = [recipient_emails]
    else:
        emails = recipient_emails
    cleaned = [e.strip() for e in emails if e and e.strip()]
    return sorted(set(cleaned))


def _send_email(*, subject: str, text_body: str, html_body: Optional[str], recipients: list[str]) -> bool:
    if not _mail_enabled():
        return False

    host = _smtp_host()
    username = _smtp_username()
    password = _smtp_password()
    sender = _from_address()

    if not host:
        logger.debug("SMTP host not configured; skipping email.")
        return False
    if not sender:
        logger.debug("MAIL_FROM/MAIL_DEFAULT_SENDER not configured; skipping email.")
        return False
    if not recipients:
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    try:
        port = _smtp_port()
        use_tls = _smtp_use_tls()
        context = ssl.create_default_context()

        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            if use_tls:
                server.starttls(context=context)
                server.ehlo()
            if username:
                server.login(username, password)
            server.send_message(msg)
        return True
    except Exception as exc:
        logger.warning("Email send failed: %s", exc)
        return False


def send_job_failure_notification(job_name: str, job_id: str, error_message: str, recipient_emails: Sequence[str] | str) -> bool:
    recipients = _normalize_recipients(recipient_emails)
    if not recipients:
        return False

    subject = f"Job Failure: {job_name}"
    text_body = (
        "Job Execution Failed\n"
        "====================\n\n"
        f"Job Name: {job_name}\n"
        f"Job ID: {job_id}\n"
        f"Error: {error_message}\n"
    )
    html_body = (
        "<html><body style=\"font-family: Arial, sans-serif; color: #333;\">"
        "<h2 style=\"color: #d32f2f;\">Job Execution Failed</h2>"
        "<ul>"
        f"<li><strong>Job Name:</strong> {job_name}</li>"
        f"<li><strong>Job ID:</strong> {job_id}</li>"
        f"<li><strong>Error:</strong> <code>{error_message}</code></li>"
        "</ul>"
        "</body></html>"
    )
    return _send_email(subject=subject, text_body=text_body, html_body=html_body, recipients=recipients)


def send_job_success_notification(
    job_name: str, job_id: str, duration_seconds: float, recipient_emails: Sequence[str] | str
) -> bool:
    recipients = _normalize_recipients(recipient_emails)
    if not recipients:
        return False

    subject = f"Job Success: {job_name}"
    text_body = (
        "Job Completed Successfully\n"
        "==========================\n\n"
        f"Job Name: {job_name}\n"
        f"Job ID: {job_id}\n"
        f"Duration: {duration_seconds:.2f}s\n"
    )
    html_body = (
        "<html><body style=\"font-family: Arial, sans-serif; color: #333;\">"
        "<h2 style=\"color: #2e7d32;\">Job Completed Successfully</h2>"
        "<ul>"
        f"<li><strong>Job Name:</strong> {job_name}</li>"
        f"<li><strong>Job ID:</strong> {job_id}</li>"
        f"<li><strong>Duration:</strong> {duration_seconds:.2f}s</li>"
        "</ul>"
        "</body></html>"
    )
    return _send_email(subject=subject, text_body=text_body, html_body=html_body, recipients=recipients)
