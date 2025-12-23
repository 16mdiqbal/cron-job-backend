import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Callable, Optional
from zoneinfo import ZoneInfo

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database.session import get_db_session
from ..models.job import Job
from ..models.job_execution import JobExecution
from ..models.notification import Notification
from ..models.user import User

logger = logging.getLogger(__name__)

_flask_app = None


def set_flask_app(app):
    global _flask_app
    _flask_app = app


@dataclass(frozen=True)
class EmailCallbacks:
    """
    Optional callbacks for email notifications.

    The current email implementation uses Flask-Mail and requires an app context,
    so scheduler execution keeps email hooks injectable for Phase 8 migration.
    """

    send_failure: Optional[Callable[[str, str, str, list[str]], bool]] = None
    send_success: Optional[Callable[[str, str, float, list[str]], bool]] = None


def _get_scheduler_timezone_name(default: str = "Asia/Tokyo") -> str:
    return (os.getenv("SCHEDULER_TIMEZONE") or default).strip() or default


def _get_scheduler_timezone(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except Exception:
        logger.warning("Invalid SCHEDULER_TIMEZONE '%s', falling back to UTC", tz_name)
        return ZoneInfo("UTC")


def _broadcast_notification(
    session: Session,
    *,
    title: str,
    message: str,
    notification_type: str,
    related_job_id: Optional[str] = None,
    related_execution_id: Optional[str] = None,
) -> None:
    user_ids = session.execute(select(User.id)).scalars().all()
    for user_id in user_ids:
        session.add(
            Notification(
                user_id=user_id,
                title=title,
                message=message,
                type=notification_type,
                related_job_id=related_job_id,
                related_execution_id=related_execution_id,
            )
        )
    session.commit()


def _broadcast_job_success(session: Session, *, job_name: str, job_id: str, execution_id: str) -> None:
    _broadcast_notification(
        session,
        title="Job Completed",
        message=f'Job "{job_name}" completed successfully.',
        notification_type="success",
        related_job_id=job_id,
        related_execution_id=execution_id,
    )


def _broadcast_job_failure(
    session: Session, *, job_name: str, job_id: str, execution_id: str, error_message: str
) -> None:
    _broadcast_notification(
        session,
        title="Job Failed",
        message=f'Job "{job_name}" failed: {error_message}',
        notification_type="error",
        related_job_id=job_id,
        related_execution_id=execution_id,
    )


def _notify_auto_paused_expired_job(session: Session, *, job: Job, today_jst: date) -> None:
    recipients: set[str] = set()
    if job.created_by:
        recipients.add(job.created_by)

    admin_ids = (
        session.execute(select(User.id).where(User.role == "admin", User.is_active.is_(True)))
        .scalars()
        .all()
    )
    recipients.update(admin_ids)

    for user_id in recipients:
        try:
            session.add(
                Notification(
                    user_id=user_id,
                    title="Job auto-paused (end date passed)",
                    message=(
                        f'Job "{job.name}" passed its end_date ({job.end_date.isoformat()} JST) '
                        "and was auto-paused."
                    ),
                    type="warning",
                    related_job_id=job.id,
                )
            )
        except Exception:
            pass
    session.commit()


def execute_job_with_app_context(job_id, job_name, job_config):
    """
    APScheduler entrypoint that ensures a Flask app context exists.

    DB work no longer requires an app context, but Flask-Mail email notifications
    still do, so this wrapper remains during migration.
    """
    if _flask_app is None:
        raise RuntimeError("Flask app not set for scheduler. Call set_flask_app(app) during startup.")
    with _flask_app.app_context():
        from ..utils.email import send_job_failure_notification, send_job_success_notification

        execute_job(
            job_id,
            job_name,
            job_config,
            trigger_type="scheduled",
            scheduler_timezone=_flask_app.config.get("SCHEDULER_TIMEZONE", _get_scheduler_timezone_name()),
            email_callbacks=EmailCallbacks(
                send_failure=send_job_failure_notification,
                send_success=send_job_success_notification,
            ),
        )


def run_end_date_maintenance_with_app_context():
    """
    APScheduler entrypoint for weekly end_date reminders / auto-pause.
    """
    if _flask_app is None:
        raise RuntimeError("Flask app not set for scheduler. Call set_flask_app(app) during startup.")
    with _flask_app.app_context():
        from ..services.end_date_maintenance import run_end_date_maintenance
        from ..scheduler import scheduler  # local import to avoid cycles

        run_end_date_maintenance(_flask_app, scheduler=scheduler)


def execute_job(
    job_id,
    job_name,
    job_config,
    trigger_type="scheduled",
    scheduler_timezone: Optional[str] = None,
    email_callbacks: Optional[EmailCallbacks] = None,
):
    """
    Execute a scheduled job by triggering GitHub Actions workflow or calling a webhook URL.

    This function is called by APScheduler when a job is triggered.
    It supports two execution modes:
    1. GitHub Actions workflow dispatch (if github_owner, github_repo, github_workflow_name provided)
    2. Generic webhook call (if target_url provided)
    """
    try:
        tz_name = (scheduler_timezone or _get_scheduler_timezone_name()).strip() or _get_scheduler_timezone_name()
        scheduler_tz = _get_scheduler_timezone(tz_name)
        logger.info("Executing job '%s' (ID: %s) at %s", job_name, job_id, datetime.now(timezone.utc).isoformat())

        with get_db_session() as session:
            job = session.get(Job, job_id)
            if not job or not job.is_active:
                logger.info("Skipping execution for inactive/missing job '%s' (ID: %s)", job_name, job_id)
                return

            today_jst = datetime.now(scheduler_tz).date()
            if job.end_date and job.end_date < today_jst:
                job.is_active = False
                session.commit()
                try:
                    from ..scheduler import scheduler as apscheduler

                    if apscheduler.get_job(job.id):
                        apscheduler.remove_job(job.id)
                except Exception:
                    pass

                _notify_auto_paused_expired_job(session, job=job, today_jst=today_jst)
                logger.info("Auto-paused expired job '%s' (ID: %s) during execution guard", job.name, job.id)
                return

            execution = JobExecution(job_id=job_id, trigger_type=trigger_type, status="running")
            session.add(execution)
            session.commit()
            session.refresh(execution)

            cfg = job_config or {}

            try:
                if cfg.get("github_owner") and cfg.get("github_repo") and cfg.get("github_workflow_name"):
                    execute_github_actions(session, job_id, job_name, cfg, execution, email_callbacks=email_callbacks)
                elif cfg.get("target_url"):
                    execute_webhook(
                        session,
                        job_id,
                        job_name,
                        cfg["target_url"],
                        cfg,
                        execution,
                        email_callbacks=email_callbacks,
                    )
                else:
                    error_msg = f"Job '{job_name}' has invalid configuration (neither GitHub Actions nor webhook URL)"
                    logger.error(error_msg)
                    execution.mark_completed("failed", error_message=error_msg)
                    session.commit()

                    if cfg.get("enable_email_notifications") and email_callbacks and email_callbacks.send_failure:
                        notification_emails = cfg.get("notification_emails", [])
                        if notification_emails:
                            try:
                                email_callbacks.send_failure(job_name, job_id, error_msg, notification_emails)
                            except Exception as exc:
                                logger.error("Failed to send failure notification: %s", exc)
            except Exception as exc:
                session.rollback()
                error_msg = f"Unexpected error executing job '{job_name}': {str(exc)}"
                logger.error(error_msg)
                execution.mark_completed("failed", error_message=error_msg)
                session.commit()

                if cfg.get("enable_email_notifications") and email_callbacks and email_callbacks.send_failure:
                    notification_emails = cfg.get("notification_emails", [])
                    if notification_emails:
                        try:
                            email_callbacks.send_failure(job_name, job_id, error_msg, notification_emails)
                        except Exception as send_exc:
                            logger.error("Failed to send failure notification: %s", send_exc)
    except Exception as exc:
        logger.exception("Scheduler execute_job error: %s", exc)


def execute_github_actions(
    session: Session,
    job_id: str,
    job_name: str,
    job_config: dict,
    execution: JobExecution,
    *,
    email_callbacks: Optional[EmailCallbacks] = None,
):
    github_token = job_config.get("github_token") or os.getenv("GITHUB_TOKEN")
    if not github_token:
        error_msg = f"GitHub token not configured. Cannot trigger workflow for job '{job_name}'"
        logger.error(error_msg)
        execution.mark_completed("failed", error_message=error_msg)
        session.commit()
        return

    owner = job_config["github_owner"]
    repo = job_config["github_repo"]
    workflow_name = job_config["github_workflow_name"]
    metadata = job_config.get("metadata", {})

    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_name}/dispatches"

    execution.execution_type = "github_actions"
    execution.target = f"{owner}/{repo}/{workflow_name}"
    session.commit()

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }

    ref = metadata.get("branchDetails", "master")
    payload = {"ref": ref, "inputs": metadata}

    logger.info("Triggering GitHub Actions workflow: %s/%s/%s", owner, repo, workflow_name)
    logger.info("Branch: %s", ref)
    logger.info("Inputs: %s", metadata)

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)

        if response.status_code == 204:
            logger.info("Job '%s' - GitHub Actions workflow triggered successfully", job_name)
            execution.mark_completed("success", response_status=204, output=f"Workflow triggered successfully on branch {ref}")
            session.commit()

            try:
                _broadcast_job_success(session, job_name=job_name, job_id=job_id, execution_id=execution.id)
                logger.info("Broadcast notification sent: Job '%s' succeeded", job_name)
            except Exception as exc:
                logger.error("Failed to broadcast success notification: %s", exc)

            if job_config.get("enable_email_notifications") and job_config.get("notify_on_success") and email_callbacks and email_callbacks.send_success:
                notification_emails = job_config.get("notification_emails", [])
                if notification_emails:
                    try:
                        duration = execution.duration_seconds if execution.duration_seconds else 0
                        email_callbacks.send_success(job_name, job_id, duration, notification_emails)
                    except Exception as exc:
                        logger.error("Failed to send success notification: %s", exc)
        else:
            error_msg = f"GitHub Actions dispatch failed. Status: {response.status_code}, Response: {response.text}"
            logger.error("Job '%s' - %s", job_name, error_msg)
            execution.mark_completed("failed", response_status=response.status_code, error_message=error_msg)
            session.commit()

            try:
                _broadcast_job_failure(
                    session,
                    job_name=job_name,
                    job_id=job_id,
                    execution_id=execution.id,
                    error_message=error_msg,
                )
                logger.info("Broadcast notification sent: Job '%s' failed", job_name)
            except Exception as exc:
                logger.error("Failed to broadcast failure notification: %s", exc)

            if job_config.get("enable_email_notifications") and email_callbacks and email_callbacks.send_failure:
                notification_emails = job_config.get("notification_emails", [])
                if notification_emails:
                    try:
                        email_callbacks.send_failure(job_name, job_id, error_msg, notification_emails)
                    except Exception as exc:
                        logger.error("Failed to send failure notification: %s", exc)

    except requests.exceptions.RequestException as exc:
        error_msg = f"GitHub Actions request failed: {str(exc)}"
        logger.error("Job '%s' - %s", job_name, error_msg)
        execution.mark_completed("failed", error_message=error_msg)
        session.commit()

        try:
            _broadcast_job_failure(
                session,
                job_name=job_name,
                job_id=job_id,
                execution_id=execution.id,
                error_message=error_msg,
            )
            logger.info("Broadcast notification sent: Job '%s' failed (exception)", job_name)
        except Exception as inner:
            logger.error("Failed to broadcast failure notification: %s", inner)

        notification_emails = job_config.get("notification_emails", [])
        if notification_emails and email_callbacks and email_callbacks.send_failure:
            try:
                email_callbacks.send_failure(job_name, job_id, error_msg, notification_emails)
            except Exception as send_error:
                logger.error("Failed to send failure notification: %s", send_error)


def execute_webhook(
    session: Session,
    job_id: str,
    job_name: str,
    target_url: str,
    job_config: dict,
    execution: JobExecution,
    *,
    email_callbacks: Optional[EmailCallbacks] = None,
):
    logger.info("Calling webhook: %s", target_url)

    execution.execution_type = "webhook"
    execution.target = target_url
    session.commit()

    try:
        payload = job_config.get("metadata") if isinstance(job_config.get("metadata"), dict) else None
        if payload:
            response = requests.post(target_url, json=payload, timeout=10)
        else:
            response = requests.get(target_url, timeout=10)
        logger.info("Job '%s' - Webhook called successfully. Status: %s", job_name, response.status_code)

        output = response.text[:1000] if len(response.text) > 1000 else response.text

        if 200 <= response.status_code < 300:
            execution.mark_completed("success", response_status=response.status_code, output=output)
            session.commit()

            try:
                _broadcast_job_success(session, job_name=job_name, job_id=job_id, execution_id=execution.id)
                logger.info("Broadcast notification sent: Job '%s' succeeded", job_name)
            except Exception as exc:
                logger.error("Failed to broadcast success notification: %s", exc)

            if job_config.get("enable_email_notifications") and job_config.get("notify_on_success") and email_callbacks and email_callbacks.send_success:
                notification_emails = job_config.get("notification_emails", [])
                if notification_emails:
                    try:
                        duration = execution.duration_seconds if execution.duration_seconds else 0
                        email_callbacks.send_success(job_name, job_id, duration, notification_emails)
                    except Exception as exc:
                        logger.error("Failed to send success notification: %s", exc)
        else:
            error_msg = f"Webhook returned status {response.status_code}"
            execution.mark_completed("failed", response_status=response.status_code, error_message=error_msg, output=output)
            session.commit()

            try:
                _broadcast_job_failure(
                    session,
                    job_name=job_name,
                    job_id=job_id,
                    execution_id=execution.id,
                    error_message=error_msg,
                )
                logger.info("Broadcast notification sent: Job '%s' failed", job_name)
            except Exception as exc:
                logger.error("Failed to broadcast failure notification: %s", exc)

            if job_config.get("enable_email_notifications") and email_callbacks and email_callbacks.send_failure:
                notification_emails = job_config.get("notification_emails", [])
                if notification_emails:
                    try:
                        email_callbacks.send_failure(job_name, job_id, error_msg, notification_emails)
                    except Exception as exc:
                        logger.error("Failed to send failure notification: %s", exc)

    except requests.exceptions.RequestException as exc:
        error_msg = f"Webhook call failed: {str(exc)}"
        logger.error("Job '%s' - %s", job_name, error_msg)
        execution.mark_completed("failed", error_message=error_msg)
        session.commit()

        try:
            _broadcast_job_failure(
                session,
                job_name=job_name,
                job_id=job_id,
                execution_id=execution.id,
                error_message=error_msg,
            )
            logger.info("Broadcast notification sent: Job '%s' failed (exception)", job_name)
        except Exception as inner:
            logger.error("Failed to broadcast failure notification: %s", inner)

        if job_config.get("enable_email_notifications") and email_callbacks and email_callbacks.send_failure:
            notification_emails = job_config.get("notification_emails", [])
            if notification_emails:
                try:
                    email_callbacks.send_failure(job_name, job_id, error_msg, notification_emails)
                except Exception as send_error:
                    logger.error("Failed to send failure notification: %s", send_error)


def trigger_job_manually(job_id, job_name, job_config):
    """
    Manually trigger a job outside of its scheduled time.
    """
    logger.info("Manually triggering job '%s' (ID: %s)", job_name, job_id)
    execute_job(job_id, job_name, job_config, trigger_type="manual")
