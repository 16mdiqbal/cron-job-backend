"""
Utility functions for creating and managing notifications.
"""
from ..models import db
from ..models.notification import Notification
from ..models.user import User


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


def broadcast_notification(title, message, notification_type='info',
                          related_job_id=None, related_execution_id=None):
    """
    Create a notification for all users in the system.
    
    Args:
        title: Notification title
        message: Notification message
        notification_type: Type of notification ('success', 'error', 'warning', 'info')
        related_job_id: Optional job ID this notification relates to
        related_execution_id: Optional execution ID this notification relates to
    
    Returns:
        List of created Notification objects
    """
    users = User.query.all()
    notifications = []
    
    for user in users:
        notification = Notification(
            user_id=user.id,
            title=title,
            message=message,
            type=notification_type,
            related_job_id=related_job_id,
            related_execution_id=related_execution_id
        )
        db.session.add(notification)
        notifications.append(notification)
    
    db.session.commit()
    return notifications


def broadcast_job_created(job_name, job_id, created_by_name):
    """Broadcast notification when a new job is created."""
    return broadcast_notification(
        title='New Job Created',
        message=f'Job "{job_name}" was created by {created_by_name}.',
        notification_type='info',
        related_job_id=job_id
    )


def broadcast_job_updated(job_name, job_id, updated_by_name):
    """Broadcast notification when a job is updated."""
    return broadcast_notification(
        title='Job Updated',
        message=f'Job "{job_name}" was updated by {updated_by_name}.',
        notification_type='info',
        related_job_id=job_id
    )


def broadcast_job_deleted(job_name, deleted_by_name):
    """Broadcast notification when a job is deleted."""
    return broadcast_notification(
        title='Job Deleted',
        message=f'Job "{job_name}" was deleted by {deleted_by_name}.',
        notification_type='warning'
    )


def broadcast_job_enabled(job_name, job_id, enabled_by_name):
    """Broadcast notification when a job is enabled."""
    return broadcast_notification(
        title='Job Enabled',
        message=f'Job "{job_name}" was enabled by {enabled_by_name}.',
        notification_type='info',
        related_job_id=job_id
    )


def broadcast_job_disabled(job_name, job_id, disabled_by_name):
    """Broadcast notification when a job is disabled."""
    return broadcast_notification(
        title='Job Disabled',
        message=f'Job "{job_name}" was disabled by {disabled_by_name}.',
        notification_type='warning',
        related_job_id=job_id
    )


def broadcast_job_failure(job_name, job_id, execution_id, error_message):
    """Broadcast notification when a job fails."""
    return broadcast_notification(
        title='Job Failed',
        message=f'Job "{job_name}" failed: {error_message}',
        notification_type='error',
        related_job_id=job_id,
        related_execution_id=execution_id
    )


def broadcast_job_success(job_name, job_id, execution_id):
    """Broadcast notification when a job succeeds."""
    return broadcast_notification(
        title='Job Completed',
        message=f'Job "{job_name}" completed successfully.',
        notification_type='success',
        related_job_id=job_id,
        related_execution_id=execution_id
    )
