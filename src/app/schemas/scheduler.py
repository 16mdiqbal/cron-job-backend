"""
Scheduler Schemas.

Response models for scheduler operational endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SchedulerStatusResponse(BaseModel):
    scheduler_running: bool
    scheduler_is_leader: bool
    scheduled_jobs_count: int
    last_resync_at: Optional[datetime] = None


class SchedulerResyncResponse(BaseModel):
    message: str
    ran_at: datetime
    db_jobs_total: int
    db_jobs_active: int
    scheduled_now: int
    scheduled_added: int
    scheduled_removed: int
    expired_auto_paused: int
    orphaned_removed: int
    invalid_cron: int

