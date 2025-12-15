import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import String
from . import db


class Notification(db.Model):
    """
    Model for user notifications.
    Stores notifications for various events like job failures, job disabled, etc.
    """
    __tablename__ = 'notifications'

    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Notification content
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'success', 'error', 'warning', 'info'
    
    # Related entity (optional)
    related_job_id = db.Column(String(36), db.ForeignKey('jobs.id', ondelete='SET NULL'), nullable=True)
    related_execution_id = db.Column(String(36), db.ForeignKey('job_executions.id', ondelete='SET NULL'), nullable=True)
    
    # Status
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    read_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic', cascade='all, delete-orphan'))
    job = db.relationship('Job', backref=db.backref('notifications', lazy='dynamic'))
    execution = db.relationship('JobExecution', backref=db.backref('notifications', lazy='dynamic'))

    def __repr__(self):
        return f'<Notification {self.id}: {self.title}>'

    def to_dict(self):
        """Convert notification to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'related_job_id': self.related_job_id,
            'related_execution_id': self.related_execution_id,
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
            db.session.commit()
