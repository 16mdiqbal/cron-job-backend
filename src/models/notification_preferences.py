import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import backref, relationship

from .base import Base


class UserNotificationPreferences(Base):
    """
    User notification preferences model.
    Stores per-user notification settings.
    """
    __tablename__ = 'user_notification_preferences'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), unique=True, nullable=False)
    
    # Email notifications
    email_on_job_success = Column(Boolean, default=True, nullable=False)
    email_on_job_failure = Column(Boolean, default=True, nullable=False)
    email_on_job_disabled = Column(Boolean, default=False, nullable=False)
    
    # Browser notifications
    browser_notifications = Column(Boolean, default=True, nullable=False)
    
    # Reports
    daily_digest = Column(Boolean, default=False, nullable=False)
    weekly_report = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Relationship
    user = relationship('User', backref=backref('notification_preferences', uselist=False))
    
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
