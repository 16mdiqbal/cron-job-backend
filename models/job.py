import uuid
import json
from datetime import datetime, timezone
from models import db


class Job(db.Model):
    """
    Job model representing a scheduled cron job.
    """
    __tablename__ = 'jobs'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False, unique=True)
    cron_expression = db.Column(db.String(100), nullable=False)
    
    # Optional: Generic webhook URL (for non-GitHub workflows)
    target_url = db.Column(db.String(500), nullable=True)
    
    # GitHub Actions Configuration
    github_owner = db.Column(db.String(255), nullable=True)
    github_repo = db.Column(db.String(255), nullable=True)
    github_workflow_name = db.Column(db.String(255), nullable=True)
    
    # Flexible metadata as JSON (renamed to avoid SQLAlchemy reserved name)
    job_metadata = db.Column(db.Text, nullable=True)
    
    # User who created this job (for ownership and authorization)
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def get_metadata(self):
        """
        Parse and return metadata as dictionary.
        """
        if self.job_metadata:
            try:
                return json.loads(self.job_metadata)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_metadata(self, metadata_dict):
        """
        Store metadata dictionary as JSON string.
        """
        if metadata_dict:
            self.job_metadata = json.dumps(metadata_dict)
        else:
            self.job_metadata = None

    def to_dict(self):
        """
        Convert Job object to dictionary for JSON serialization.
        """
        return {
            'id': self.id,
            'name': self.name,
            'cron_expression': self.cron_expression,
            'target_url': self.target_url,
            'github_owner': self.github_owner,
            'github_repo': self.github_repo,
            'github_workflow_name': self.github_workflow_name,
            'metadata': self.get_metadata(),
            'created_by': self.created_by,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Job {self.name} ({self.id})>'
