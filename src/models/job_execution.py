import uuid
from datetime import datetime, timezone
from models import db


class JobExecution(db.Model):
    """
    JobExecution model for tracking job execution history.
    
    Records every time a job is executed, including status, duration,
    and any error messages.
    """
    __tablename__ = 'job_executions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = db.Column(db.String(36), db.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False)  # success, failed, running
    trigger_type = db.Column(db.String(20), nullable=False)  # scheduled, manual
    started_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Float, nullable=True)
    
    # Execution details
    execution_type = db.Column(db.String(50), nullable=True)  # github_actions, webhook
    target = db.Column(db.String(500), nullable=True)  # URL or github workflow path
    response_status = db.Column(db.Integer, nullable=True)  # HTTP status code
    error_message = db.Column(db.Text, nullable=True)
    output = db.Column(db.Text, nullable=True)
    
    # Relationship
    job = db.relationship('Job', backref=db.backref('executions', lazy=True, cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<JobExecution {self.id} - Job:{self.job_id} - Status:{self.status}>'
    
    def to_dict(self):
        """Convert execution object to dictionary."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'status': self.status,
            'trigger_type': self.trigger_type,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'execution_type': self.execution_type,
            'target': self.target,
            'response_status': self.response_status,
            'error_message': self.error_message,
            'output': self.output
        }
    
    def mark_completed(self, status, response_status=None, error_message=None, output=None):
        """
        Mark execution as completed and calculate duration.
        
        Args:
            status (str): Final status (success or failed)
            response_status (int): HTTP response status code
            error_message (str): Error message if failed
            output (str): Execution output or response body
        """
        self.completed_at = datetime.now(timezone.utc)
        self.status = status
        self.response_status = response_status
        self.error_message = error_message
        self.output = output
        
        # Calculate duration
        if self.started_at and self.completed_at:
            duration = self.completed_at - self.started_at
            self.duration_seconds = duration.total_seconds()
