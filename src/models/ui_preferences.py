import uuid
import json
from datetime import datetime, timezone
from . import db


class UserUiPreferences(db.Model):
    """
    Per-user UI preferences (cross-device).
    """
    __tablename__ = 'user_ui_preferences'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), unique=True, nullable=False)

    # Store as JSON string to stay flexible without migrations.
    jobs_table_columns = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = db.relationship('User', backref=db.backref('ui_preferences', uselist=False))

    def get_jobs_table_columns(self):
        if not self.jobs_table_columns:
            return None
        try:
            val = json.loads(self.jobs_table_columns)
            return val if isinstance(val, dict) else None
        except Exception:
            return None

    def set_jobs_table_columns(self, value):
        if value is None:
            self.jobs_table_columns = None
            return
        if not isinstance(value, dict):
            raise ValueError('jobs_table_columns must be an object.')
        self.jobs_table_columns = json.dumps(value)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'jobs_table_columns': self.get_jobs_table_columns(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

