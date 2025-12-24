"""
Read-only Executions API Schemas (Response Parity with Flask).

These schemas intentionally match Flask v1 response shapes for Phase 4C:
- GET /api/jobs/<job_id>/executions
- GET /api/jobs/<job_id>/executions/<execution_id>
- GET /api/jobs/<job_id>/executions/stats
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class ExecutionReadPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    job_id: str
    status: str
    trigger_type: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    execution_type: Optional[str] = None
    target: Optional[str] = None
    response_status: Optional[int] = None
    error_message: Optional[str] = None
    output: Optional[str] = None


class JobExecutionsReadResponse(BaseModel):
    job_id: str
    job_name: str
    total_executions: int
    executions: List[ExecutionReadPayload]


class JobSummary(BaseModel):
    id: str
    name: str


class JobExecutionDetailReadResponse(BaseModel):
    job: JobSummary
    execution: ExecutionReadPayload


class JobExecutionStatistics(BaseModel):
    total_executions: int
    success_count: int
    failed_count: int
    running_count: int
    success_rate: float
    average_duration_seconds: Optional[float] = None


class JobExecutionStatsReadResponse(BaseModel):
    job_id: str
    job_name: str
    statistics: JobExecutionStatistics
    latest_execution: Optional[ExecutionReadPayload] = None


class ExecutionWithJobReadPayload(ExecutionReadPayload):
    model_config = ConfigDict(extra="ignore")

    job_name: Optional[str] = None
    github_repo: Optional[str] = None


class ExecutionsListReadResponse(BaseModel):
    executions: List[ExecutionWithJobReadPayload]
    total: int
    page: int
    limit: int
    total_pages: int


class ExecutionGetReadResponse(BaseModel):
    execution: ExecutionWithJobReadPayload


class ExecutionStatisticsReadResponse(BaseModel):
    total_executions: int
    successful_executions: int
    failed_executions: int
    running_executions: int
    success_rate: float
    average_duration_seconds: float
    range: Dict[str, Optional[str]]
