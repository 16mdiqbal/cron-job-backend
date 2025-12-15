"""
Utility functions for creating and managing notifications.
"""
from ..models import db
from ..models.notification import Notification


def create_notification(user_id, title, message, notification_type='info', 
                       related_job_id=None, related_execution_id=None):
    """
    Create a new notification for a user.
    
    Args:
        user_id: The user ID to receive the notification
        title: Notification title
        message: Notification message
        notification_type: Type of notification ('success', 'error', 'warning', 'info')
        related_job_id: Optional job ID this notification relates to
        related_execution_id: Optional execution ID this notification relates to
    
    Returns:
        The created Notification object
    """
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
        related_job_id=related_job_id,
        related_execution_id=related_execution_id
    )
    
    db.session.add(notification)
    db.session.commit()
    
    return notification


def create_job_disabled_notification(user_id, job_name, job_id):
    """Create notification when a job is disabled."""
    return create_notification(
        user_id=user_id,
        title='Job Disabled',
        message=f'Your job "{job_name}" has been disabled.',
        notification_type='warning',
        related_job_id=job_id
    )


def create_job_failure_notification(user_id, job_name, job_id, execution_id, error_message):
    """Create notification when a job fails."""
    return create_notification(
        user_id=user_id,
        title='Job Failed',
        message=f'Job "{job_name}" failed: {error_message}',
        notification_type='error',
        related_job_id=job_id,
        related_execution_id=execution_id
    )


def create_job_success_notification(user_id, job_name, job_id, execution_id):
    """Create notification when a job succeeds."""
    return create_notification(
        user_id=user_id,
        title='Job Completed',
        message=f'Job "{job_name}" completed successfully.',
        notification_type='success',
        related_job_id=job_id,
        related_execution_id=execution_id
    )
