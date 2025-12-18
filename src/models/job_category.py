import uuid
from datetime import datetime, timezone
from . import db


class JobCategory(db.Model):
    __tablename__ = 'job_categories'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = db.Column(db.String(100), nullable=False, unique=True, index=True)
    name = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def to_dict(self):
        return {
            'id': self.id,
            'slug': self.slug,
            'name': self.name,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

