from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class IssueOut(BaseModel):
    id: UUID
    project_id: UUID
    github_issue_id: int
    number: int
    title: str
    body: str | None
    state: Literal["open", "closed"]
    state_reason: str | None
    html_url: str
    author_login: str | None
    assignees: list[str]
    labels: list[str]
    milestone: str | None
    comments_count: int
    github_created_at: datetime
    github_updated_at: datetime
    github_closed_at: datetime | None
    synced_at: datetime


class IssueSyncRequest(BaseModel):
    project_id: UUID


class IssueSyncOut(BaseModel):
    project_id: UUID
    synced: int
