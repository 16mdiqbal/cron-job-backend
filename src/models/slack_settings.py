import uuid
from datetime import datetime, timezone
from . import db


class SlackSettings(db.Model):
    """
    Global Slack integration settings (admin-managed).

    Note: This stores the webhook URL in plaintext in the database.
    """
    __tablename__ = 'slack_settings'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    is_enabled = db.Column(db.Boolean, default=False, nullable=False)
    webhook_url = db.Column(db.Text, nullable=True)
    channel = db.Column(db.String(255), nullable=True)

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
            'is_enabled': self.is_enabled,
            'webhook_url': self.webhook_url,
            'channel': self.channel,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

