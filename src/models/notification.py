import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_object_session
from sqlalchemy.orm import backref, relationship

from .base import Base


class Notification(Base):
    """
    Model for user notifications.
    Stores notifications for various events like job failures, job disabled, etc.
    """
    __tablename__ = 'notifications'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Notification content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=False)  # 'success', 'error', 'warning', 'info'
    
    # Related entity (optional)
    related_job_id = Column(String(36), ForeignKey('jobs.id', ondelete='SET NULL'), nullable=True)
    related_execution_id = Column(String(36), ForeignKey('job_executions.id', ondelete='SET NULL'), nullable=True)
    
    # Status
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime, nullable=True)
    
    # Timestamps - Store in UTC with timezone awareness
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    user = relationship('User', backref=backref('notifications', cascade='all, delete-orphan'))
    job = relationship('Job', backref=backref('notifications'))
    execution = relationship('JobExecution', backref=backref('notifications'))

    def __repr__(self):
        return f'<Notification {self.id}: {self.title}>'

    def to_dict(self):
        """Convert notification to dictionary for JSON serialization."""
        # Ensure datetimes have timezone info (assume UTC if naive)
        created_at_str = None
        if self.created_at:
            if self.created_at.tzinfo is None:
                # Naive datetime - assume it's UTC
                created_at_aware = self.created_at.replace(tzinfo=timezone.utc)
            else:
                created_at_aware = self.created_at
            created_at_str = created_at_aware.isoformat()
        
        read_at_str = None
        if self.read_at:
            if self.read_at.tzinfo is None:
                read_at_aware = self.read_at.replace(tzinfo=timezone.utc)
            else:
                read_at_aware = self.read_at
            read_at_str = read_at_aware.isoformat()
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'related_job_id': self.related_job_id,
            'related_execution_id': self.related_execution_id,
            'is_read': self.is_read,
            'read_at': read_at_str,
            'created_at': created_at_str
        }

    async def mark_as_read(self, db: Optional[AsyncSession] = None, *, commit: bool = True) -> bool:
        """
        Mark notification as read and persist the change.

        Returns True if the notification was updated, otherwise False.
        """
        if self.is_read:
            return False

        self.is_read = True
        self.read_at = datetime.now(timezone.utc)

        if not commit:
            return True

        session = db or async_object_session(self)
        if session is None:
            raise RuntimeError("Notification is not attached to a session; pass `db` to persist changes.")

        await session.commit()
        return True
