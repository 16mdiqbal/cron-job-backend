import uuid
from datetime import datetime, timezone
from passlib.hash import pbkdf2_sha256
from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship

from .base import Base


class User(Base):
    """
    User model for authentication and authorization.
    
    Roles:
    - admin: Full access to all operations (CRUD + manual trigger)
    - user: Can create, read, update own jobs, and trigger own jobs
    - viewer: Read-only access to all jobs
    """
    __tablename__ = 'users'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default='viewer')  # admin, user, viewer
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Relationship: User can have multiple jobs
    jobs = relationship('Job', backref='owner', foreign_keys='Job.created_by')
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
    
    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = pbkdf2_sha256.hash(password)
    
    def check_password(self, password):
        """Verify the user's password."""
        return pbkdf2_sha256.verify(password, self.password_hash)
    
    def to_dict(self):
        """Convert user object to dictionary (excluding password)."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def validate_role(role):
        """Validate that the role is one of the allowed values."""
        allowed_roles = ['admin', 'user', 'viewer']
        return role in allowed_roles
