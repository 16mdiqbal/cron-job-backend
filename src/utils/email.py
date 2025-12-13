"""
Email notification utility for sending job failure alerts.
"""

import logging
from flask_mail import Mail, Message
from flask import current_app

logger = logging.getLogger(__name__)

# Initialize Mail object (will be configured in app factory)
mail = Mail()


def send_job_failure_notification(job_name, job_id, error_message, recipient_emails):
    """
    Send an email notification when a job fails.
    
    Args:
        job_name (str): The name of the failed job
        job_id (str): The unique identifier of the job
        error_message (str): The error message from the failed job
        recipient_emails (list or str): Email address(es) to send notification to
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    
    # Check if email notifications are enabled
    if not current_app.config.get('MAIL_ENABLED', True):
        logger.debug("Email notifications are disabled")
        return False
    
    # Check if email is configured
    if not current_app.config.get('MAIL_USERNAME'):
        logger.warning("Email is not configured. Skipping notification.")
        return False
    
    # Convert single email to list
    if isinstance(recipient_emails, str):
        recipient_emails = [recipient_emails]
    
    # Filter out empty emails
    recipient_emails = [email for email in recipient_emails if email]
    
    if not recipient_emails:
        logger.warning(f"No recipient emails configured for job '{job_name}'")
        return False
    
    try:
        subject = f"🔴 Job Failure Alert: {job_name}"
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #d32f2f;">Job Execution Failed</h2>
                    <p>The following scheduled job has failed:</p>
                    
                    <div style="background-color: #f5f5f5; padding: 15px; border-left: 4px solid #d32f2f; margin: 20px 0;">
                        <p><strong>Job Name:</strong> {job_name}</p>
                        <p><strong>Job ID:</strong> {job_id}</p>
                        <p><strong>Error:</strong> <code style="background-color: #fff3cd; padding: 5px; border-radius: 3px;">{error_message}</code></p>
                    </div>
                    
                    <p style="color: #666; font-size: 14px;">
                        Please review your job configuration and logs to identify and resolve the issue.
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="color: #999; font-size: 12px;">
                        This is an automated notification from Cron Job Scheduler. Please do not reply to this email.
                    </p>
                </div>
            </body>
        </html>
        """
        
        text_body = f"""
        Job Execution Failed
        ====================
        
        Job Name: {job_name}
        Job ID: {job_id}
        Error: {error_message}
        
        Please review your job configuration and logs to identify and resolve the issue.
        
        This is an automated notification from Cron Job Scheduler.
        """
        
        msg = Message(
            subject=subject,
            recipients=recipient_emails,
            html=html_body,
            body=text_body
        )
        
        mail.send(msg)
        logger.info(f"Failure notification sent for job '{job_name}' to {', '.join(recipient_emails)}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send email notification for job '{job_name}': {str(e)}")
        return False


def send_job_success_notification(job_name, job_id, duration_seconds, recipient_emails):
    """
    Send an email notification when a job succeeds (optional, for critical jobs).
    
    Args:
        job_name (str): The name of the successful job
        job_id (str): The unique identifier of the job
        duration_seconds (float): The duration of job execution in seconds
        recipient_emails (list or str): Email address(es) to send notification to
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    
    # Check if email notifications are enabled
    if not current_app.config.get('MAIL_ENABLED', True):
        logger.debug("Email notifications are disabled")
        return False
    
    # Check if email is configured
    if not current_app.config.get('MAIL_USERNAME'):
        logger.warning("Email is not configured. Skipping notification.")
        return False
    
    # Convert single email to list
    if isinstance(recipient_emails, str):
        recipient_emails = [recipient_emails]
    
    # Filter out empty emails
    recipient_emails = [email for email in recipient_emails if email]
    
    if not recipient_emails:
        logger.debug(f"No recipient emails configured for job '{job_name}'")
        return False
    
    try:
        subject = f"✅ Job Success: {job_name}"
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #2e7d32;">Job Completed Successfully</h2>
                    <p>The following scheduled job has completed successfully:</p>
                    
                    <div style="background-color: #f5f5f5; padding: 15px; border-left: 4px solid #2e7d32; margin: 20px 0;">
                        <p><strong>Job Name:</strong> {job_name}</p>
                        <p><strong>Job ID:</strong> {job_id}</p>
                        <p><strong>Duration:</strong> {duration_seconds:.2f} seconds</p>
                    </div>
                    
                    <p style="color: #666; font-size: 14px;">
                        No action is required. This is an informational notification.
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="color: #999; font-size: 12px;">
                        This is an automated notification from Cron Job Scheduler. Please do not reply to this email.
                    </p>
                </div>
            </body>
        </html>
        """
        
        text_body = f"""
        Job Completed Successfully
        ==========================
        
        Job Name: {job_name}
        Job ID: {job_id}
        Duration: {duration_seconds:.2f} seconds
        
        No action is required. This is an informational notification.
        
        This is an automated notification from Cron Job Scheduler.
        """
        
        msg = Message(
            subject=subject,
            recipients=recipient_emails,
            html=html_body,
            body=text_body
        )
        
        mail.send(msg)
        logger.info(f"Success notification sent for job '{job_name}' to {', '.join(recipient_emails)}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send success notification for job '{job_name}': {str(e)}")
        return False
