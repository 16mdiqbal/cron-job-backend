import uuid
from datetime import datetime, timezone
from . import db


class UserNotificationPreferences(db.Model):
    """
    User notification preferences model.
    Stores per-user notification settings.
    """
    __tablename__ = 'user_notification_preferences'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), unique=True, nullable=False)
    
    # Email notifications
    email_on_job_success = db.Column(db.Boolean, default=True, nullable=False)
    email_on_job_failure = db.Column(db.Boolean, default=True, nullable=False)
    email_on_job_disabled = db.Column(db.Boolean, default=False, nullable=False)
    
    # Browser notifications
    browser_notifications = db.Column(db.Boolean, default=True, nullable=False)
    
    # Reports
    daily_digest = db.Column(db.Boolean, default=False, nullable=False)
    weekly_report = db.Column(db.Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Relationship
    user = db.relationship('User', backref=db.backref('notification_preferences', uselist=False))
    
    def __repr__(self):
        return f'<UserNotificationPreferences user_id={self.user_id}>'
    
    def to_dict(self):
        """Convert preferences object to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'email_on_job_success': self.email_on_job_success,
            'email_on_job_failure': self.email_on_job_failure,
            'email_on_job_disabled': self.email_on_job_disabled,
            'browser_notifications': self.browser_notifications,
            'daily_digest': self.daily_digest,
            'weekly_report': self.weekly_report,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
