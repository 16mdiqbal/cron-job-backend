import logging
import requests
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask import current_app
from ..models import db, JobExecution
from ..models.job import Job
from ..models.user import User
from ..utils.email import send_job_failure_notification, send_job_success_notification
from ..utils.notifications import broadcast_job_success, broadcast_job_failure
from ..services.end_date_maintenance import run_end_date_maintenance

logger = logging.getLogger(__name__)

_flask_app = None


def set_flask_app(app):
    global _flask_app
    _flask_app = app


def execute_job_with_app_context(job_id, job_name, job_config):
    """
    APScheduler entrypoint that ensures a Flask app context exists.

    Flask-SQLAlchemy sessions are scoped to the Flask application context; when APScheduler
    runs jobs on background threads there is no context by default.
    """
    if _flask_app is None:
        raise RuntimeError("Flask app not set for scheduler. Call set_flask_app(app) during startup.")
    with _flask_app.app_context():
        execute_job(job_id, job_name, job_config, trigger_type='scheduled')


def run_end_date_maintenance_with_app_context():
    """
    APScheduler entrypoint for weekly end_date reminders / auto-pause.
    """
    if _flask_app is None:
        raise RuntimeError("Flask app not set for scheduler. Call set_flask_app(app) during startup.")
    with _flask_app.app_context():
        from ..scheduler import scheduler  # local import to avoid cycles
        run_end_date_maintenance(_flask_app, scheduler=scheduler)


def execute_job(job_id, job_name, job_config, trigger_type='scheduled'):
    """
    Execute a scheduled job by triggering GitHub Actions workflow or calling a webhook URL.
    
    This function is called by APScheduler when a job is triggered.
    It supports two execution modes:
    1. GitHub Actions workflow dispatch (if github_owner, github_repo, github_workflow_name provided)
    2. Generic webhook call (if target_url provided)
    
    Args:
        job_id (str): The unique identifier of the job
        job_name (str): The name of the job
        job_config (dict): Job configuration containing:
            - target_url (optional): Generic webhook URL
            - github_owner (optional): GitHub repository owner
            - github_repo (optional): GitHub repository name
            - github_workflow_name (optional): GitHub workflow file name
            - metadata (optional): Job metadata to pass as workflow inputs
            - enable_email_notifications (optional): Whether email notifications are enabled
            - notification_emails (optional): List of emails to notify on failure
            - notify_on_success (optional): Whether to notify on success
        trigger_type (str): Type of trigger ('scheduled' or 'manual')
    """
    logger.info(f"Executing job '{job_name}' (ID: {job_id}) at {datetime.now(timezone.utc).isoformat()}")

    # Guard: skip executions for paused/expired jobs (auto-pause on first trigger after end_date).
    try:
        job = Job.query.get(job_id)
        if not job or not job.is_active:
            logger.info(f"Skipping execution for inactive/missing job '{job_name}' (ID: {job_id})")
            return

        tz_name = current_app.config.get('SCHEDULER_TIMEZONE', 'Asia/Tokyo')
        today_jst = datetime.now(ZoneInfo(tz_name)).date()
        if job.end_date and job.end_date < today_jst:
            job.is_active = False
            db.session.commit()
            try:
                from ..scheduler import scheduler
                if scheduler.get_job(job.id):
                    scheduler.remove_job(job.id)
            except Exception:
                pass

            recipients: set[str] = set()
            if job.created_by:
                recipients.add(job.created_by)
            for admin in User.query.filter_by(role='admin', is_active=True).all():
                recipients.add(admin.id)

            for user_id in recipients:
                try:
                    from ..utils.notifications import create_notification
                    create_notification(
                        user_id=user_id,
                        title='Job auto-paused (end date passed)',
                        message=f'Job \"{job.name}\" passed its end_date ({job.end_date.isoformat()} JST) and was auto-paused.',
                        notification_type='warning',
                        related_job_id=job.id,
                    )
                except Exception:
                    pass

            logger.info(f"Auto-paused expired job '{job.name}' (ID: {job.id}) during execution guard")
            return
    except Exception as e:
        logger.warning(f"End-date guard failed for job '{job_name}' (ID: {job_id}): {e}")
    
    # Create execution record
    execution = JobExecution(job_id=job_id, trigger_type=trigger_type, status='running')
    db.session.add(execution)
    db.session.commit()
    
    try:
        # Priority 1: GitHub Actions workflow dispatch
        if job_config.get('github_owner') and job_config.get('github_repo') and job_config.get('github_workflow_name'):
            result = execute_github_actions(job_id, job_name, job_config, execution)
        
        # Priority 2: Generic webhook URL
        elif job_config.get('target_url'):
            result = execute_webhook(job_id, job_name, job_config['target_url'], job_config, execution)
        
        else:
            error_msg = f"Job '{job_name}' has no valid target (neither GitHub Actions nor webhook URL)"
            logger.error(error_msg)
            execution.mark_completed('failed', error_message=error_msg)
            db.session.commit()
            
            # Send failure notification only if enabled
            if job_config.get('enable_email_notifications'):
                notification_emails = job_config.get('notification_emails', [])
                if notification_emails:
                    try:
                        send_job_failure_notification(job_name, job_id, error_msg, notification_emails)
                    except Exception as e:
                        logger.error(f"Failed to send failure notification: {str(e)}")
        
    except Exception as e:
        error_msg = f"Unexpected error executing job '{job_name}': {str(e)}"
        logger.error(error_msg)
        execution.mark_completed('failed', error_message=error_msg)
        db.session.commit()
        
        # Send failure notification only if enabled
        if job_config.get('enable_email_notifications'):
            notification_emails = job_config.get('notification_emails', [])
            if notification_emails:
                try:
                    send_job_failure_notification(job_name, job_id, error_msg, notification_emails)
                except Exception as e:
                    logger.error(f"Failed to send failure notification: {str(e)}")


def execute_github_actions(job_id, job_name, job_config, execution):
    """
    Trigger a GitHub Actions workflow dispatch.
    
    Args:
        job_name (str): The name of the job
        job_config (dict): Configuration with github_owner, github_repo, github_workflow_name, metadata
        execution (JobExecution): The execution record to update
    """
    github_token = job_config.get('github_token') or os.getenv('GITHUB_TOKEN')
    if not github_token:
        error_msg = f"GitHub token not configured. Cannot trigger workflow for job '{job_name}'"
        logger.error(error_msg)
        execution.mark_completed('failed', error_message=error_msg)
        db.session.commit()
        return
    
    owner = job_config['github_owner']
    repo = job_config['github_repo']
    workflow_name = job_config['github_workflow_name']
    metadata = job_config.get('metadata', {})
    
    # GitHub API endpoint for workflow dispatch
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_name}/dispatches"
    
    # Update execution record with target
    execution.execution_type = 'github_actions'
    execution.target = f"{owner}/{repo}/{workflow_name}"
    db.session.commit()
    
    headers = {
        'Authorization': f'Bearer {github_token}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
    }
    
    # Use branch from metadata or default to 'master'
    ref = metadata.get('branchDetails', 'master')
    
    payload = {
        'ref': ref,
        'inputs': metadata  # Pass all metadata as workflow inputs
    }
    
    logger.info(f"Triggering GitHub Actions workflow: {owner}/{repo}/{workflow_name}")
    logger.info(f"Branch: {ref}")
    logger.info(f"Inputs: {metadata}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 204:
            logger.info(f"Job '{job_name}' - GitHub Actions workflow triggered successfully")
            execution.mark_completed('success', response_status=204, output=f"Workflow triggered successfully on branch {ref}")
            db.session.commit()
            
            # Broadcast success notification to all users
            try:
                broadcast_job_success(job_name, job_id, execution.id)
                logger.info(f"Broadcast notification sent: Job '{job_name}' succeeded")
            except Exception as e:
                logger.error(f"Failed to broadcast success notification: {str(e)}")
            
            # Send success notification only if enabled
            if job_config.get('enable_email_notifications') and job_config.get('notify_on_success'):
                notification_emails = job_config.get('notification_emails', [])
                if notification_emails:
                    try:
                        duration = execution.duration_seconds if execution.duration_seconds else 0
                        send_job_success_notification(job_name, job_id, duration, notification_emails)
                    except Exception as e:
                        logger.error(f"Failed to send success notification: {str(e)}")
        else:
            error_msg = f"GitHub Actions dispatch failed. Status: {response.status_code}, Response: {response.text}"
            logger.error(f"Job '{job_name}' - {error_msg}")
            execution.mark_completed('failed', response_status=response.status_code, error_message=error_msg)
            db.session.commit()
            
            # Broadcast failure notification to all users
            try:
                broadcast_job_failure(job_name, job_id, execution.id, error_msg)
                logger.info(f"Broadcast notification sent: Job '{job_name}' failed")
            except Exception as e:
                logger.error(f"Failed to broadcast failure notification: {str(e)}")
            
            # Send failure notification only if enabled
            if job_config.get('enable_email_notifications'):
                notification_emails = job_config.get('notification_emails', [])
                if notification_emails:
                    try:
                        send_job_failure_notification(job_name, job_id, error_msg, notification_emails)
                    except Exception as e:
                        logger.error(f"Failed to send failure notification: {str(e)}")
    
    except requests.exceptions.RequestException as e:
        error_msg = f"GitHub Actions request failed: {str(e)}"
        logger.error(f"Job '{job_name}' - {error_msg}")
        execution.mark_completed('failed', error_message=error_msg)
        db.session.commit()

        # Broadcast failure notification to all users
        try:
            broadcast_job_failure(job_name, job_id, execution.id, error_msg)
            logger.info(f"Broadcast notification sent: Job '{job_name}' failed (exception)")
        except Exception as e:
            logger.error(f"Failed to broadcast failure notification: {str(e)}")

        # Send failure notification
        notification_emails = job_config.get('notification_emails', [])
        if notification_emails:
            try:
                send_job_failure_notification(job_name, job_id, error_msg, notification_emails)
            except Exception as send_error:
                logger.error(f"Failed to send failure notification: {str(send_error)}")


def execute_webhook(job_id, job_name, target_url, job_config, execution):
    """
    Call a generic webhook URL.
    
    Args:
        job_id (str): The unique identifier of the job
        job_name (str): The name of the job
        target_url (str): The webhook URL to call
        job_config (dict): Job configuration
        execution (JobExecution): The execution record to update
    """
    logger.info(f"Calling webhook: {target_url}")
    
    # Update execution record with target
    execution.execution_type = 'webhook'
    execution.target = target_url
    db.session.commit()
    
    try:
        payload = job_config.get('metadata') if isinstance(job_config.get('metadata'), dict) else None
        if payload:
            response = requests.post(target_url, json=payload, timeout=10)
        else:
            response = requests.get(target_url, timeout=10)
        logger.info(f"Job '{job_name}' - Webhook called successfully. Status: {response.status_code}")
        
        # Truncate response text if too long
        output = response.text[:1000] if len(response.text) > 1000 else response.text
        
        if response.status_code >= 200 and response.status_code < 300:
            execution.mark_completed('success', response_status=response.status_code, output=output)
            db.session.commit()
            
            # Broadcast success notification to all users
            try:
                broadcast_job_success(job_name, job_id, execution.id)
                logger.info(f"Broadcast notification sent: Job '{job_name}' succeeded")
            except Exception as e:
                logger.error(f"Failed to broadcast success notification: {str(e)}")
            
            # Send success notification only if enabled
            if job_config.get('enable_email_notifications') and job_config.get('notify_on_success'):
                notification_emails = job_config.get('notification_emails', [])
                if notification_emails:
                    try:
                        duration = execution.duration_seconds if execution.duration_seconds else 0
                        send_job_success_notification(job_name, job_id, duration, notification_emails)
                    except Exception as e:
                        logger.error(f"Failed to send success notification: {str(e)}")
        else:
            error_msg = f"Webhook returned status {response.status_code}"
            execution.mark_completed('failed', response_status=response.status_code, 
                                   error_message=error_msg, 
                                   output=output)
            db.session.commit()
            
            # Broadcast failure notification to all users
            try:
                broadcast_job_failure(job_name, job_id, execution.id, error_msg)
                logger.info(f"Broadcast notification sent: Job '{job_name}' failed")
            except Exception as e:
                logger.error(f"Failed to broadcast failure notification: {str(e)}")
            
            # Send failure notification only if enabled
            if job_config.get('enable_email_notifications'):
                notification_emails = job_config.get('notification_emails', [])
                if notification_emails:
                    try:
                        send_job_failure_notification(job_name, job_id, error_msg, notification_emails)
                    except Exception as e:
                        logger.error(f"Failed to send failure notification: {str(e)}")
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Webhook call failed: {str(e)}"
        logger.error(f"Job '{job_name}' - {error_msg}")
        execution.mark_completed('failed', error_message=error_msg)
        db.session.commit()
        
        # Broadcast failure notification to all users
        try:
            broadcast_job_failure(job_name, job_id, execution.id, error_msg)
            logger.info(f"Broadcast notification sent: Job '{job_name}' failed (exception)")
        except Exception as e:
            logger.error(f"Failed to broadcast failure notification: {str(e)}")
        
        # Send failure notification only if enabled
        if job_config.get('enable_email_notifications'):
            notification_emails = job_config.get('notification_emails', [])
            if notification_emails:
                try:
                    send_job_failure_notification(job_name, job_id, error_msg, notification_emails)
                except Exception as send_error:
                    logger.error(f"Failed to send failure notification: {str(send_error)}")


def trigger_job_manually(job_id, job_name, job_config):
    """
    Manually trigger a job outside of its scheduled time.
    
    This function is called when the /api/jobs/<job_id>/trigger endpoint is invoked.
    
    Args:
        job_id (str): The unique identifier of the job
        job_name (str): The name of the job
        job_config (dict): Job configuration
    """
    logger.info(f"Manually triggering job '{job_name}' (ID: {job_id})")
    execute_job(job_id, job_name, job_config, trigger_type='manual')
