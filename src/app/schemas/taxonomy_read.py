"""
Read-only Taxonomy Schemas (Response Parity with Flask).

Phase 4E implements read-only endpoints:
- GET /api/v2/job-categories -> { "categories": [...] }
- GET /api/v2/pic-teams      -> { "pic_teams": [...] }
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class JobCategoryReadPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    slug: str
    name: str
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PicTeamReadPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    slug: str
    name: str
    slack_handle: Optional[str] = None
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class JobCategoriesReadResponse(BaseModel):
    categories: List[JobCategoryReadPayload]


class PicTeamsReadResponse(BaseModel):
    pic_teams: List[PicTeamReadPayload]

