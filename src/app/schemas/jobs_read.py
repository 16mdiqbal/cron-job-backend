"""
Read-only Jobs API Schemas (Response Parity with Flask).

These schemas intentionally match Flask v1 response shapes:
- GET /api/jobs   -> { "count": int, "jobs": [...] }
- GET /api/jobs/<id> -> { "job": {...} }
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class JobReadPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    cron_expression: str
    target_url: Optional[str] = None
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None
    github_workflow_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    category: str
    end_date: Optional[str] = None
    pic_team: Optional[str] = None
    enable_email_notifications: bool
    notification_emails: List[str]
    notify_on_success: bool
    created_by: Optional[str] = None
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # Parity fields (added by read endpoints)
    last_execution_at: Optional[str] = None
    next_execution_at: Optional[str] = None


class JobListReadResponse(BaseModel):
    count: int
    jobs: List[JobReadPayload]


class JobGetReadResponse(BaseModel):
    job: JobReadPayload

