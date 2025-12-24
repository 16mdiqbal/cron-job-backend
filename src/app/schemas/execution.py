"""
Execution Pydantic Schemas.

Request/response models for job execution history endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""
    SUCCESS = "success"
    FAILED = "failed"
    RUNNING = "running"


class TriggerType(str, Enum):
    """Trigger type enumeration."""
    SCHEDULED = "scheduled"
    MANUAL = "manual"


class ExecutionType(str, Enum):
    """Execution type enumeration."""
    GITHUB_ACTIONS = "github_actions"
    WEBHOOK = "webhook"


# ============================================================================
# Response Schemas
# ============================================================================

class ExecutionResponse(BaseModel):
    """Job execution response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    job_id: str
    status: ExecutionStatus
    trigger_type: TriggerType
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    execution_type: Optional[str] = None
    target: Optional[str] = None
    response_status: Optional[int] = None
    error_message: Optional[str] = None
    output: Optional[str] = None
    
    # Joined fields (added during response)
    job_name: Optional[str] = None


class ExecutionListResponse(BaseModel):
    """Paginated execution list response."""
    success: bool = True
    executions: List[ExecutionResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ExecutionStats(BaseModel):
    """Execution statistics response."""
    total_executions: int
    success_count: int
    failed_count: int
    running_count: int
    success_rate: float = Field(description="Percentage (0-100)")
    avg_duration_seconds: Optional[float] = None
    
    # Time-based stats
    executions_last_hour: int = 0
    executions_last_24h: int = 0
    executions_last_7d: int = 0


class ExecutionTimelineItem(BaseModel):
    """Single item in execution timeline."""
    timestamp: datetime
    count: int
    success_count: int
    failed_count: int


class ExecutionTimelineResponse(BaseModel):
    """Execution timeline for charts."""
    success: bool = True
    timeline: List[ExecutionTimelineItem]
    period: str = Field(description="hour, day, week, month")


class JobExecutionSummary(BaseModel):
    """Summary of executions for a specific job."""
    job_id: str
    job_name: str
    total_executions: int
    success_count: int
    failed_count: int
    last_execution: Optional[ExecutionResponse] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None


class DashboardStats(BaseModel):
    """Dashboard statistics combining jobs and executions."""
    # Job stats
    total_jobs: int
    active_jobs: int
    inactive_jobs: int
    
    # Execution stats
    total_executions: int
    success_rate: float
    
    # Recent activity
    executions_today: int
    failures_today: int
    
    # Scheduler info
    scheduler_running: bool
    scheduled_jobs_count: int
    
    # Upcoming
    next_scheduled_job: Optional[str] = None
    next_run_time: Optional[datetime] = None
