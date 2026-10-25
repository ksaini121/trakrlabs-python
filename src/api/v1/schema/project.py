from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field
from services.github_issues import REPO_NAME_REGEX


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = None
    github_repo_name: str = Field(pattern=REPO_NAME_REGEX)
    # Defaults to the creator when omitted.
    project_admin_id: UUID | None = None


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    github_repo_name: str | None = Field(default=None, pattern=REPO_NAME_REGEX)
    project_admin_id: UUID | None = None


class ProjectOut(BaseModel):
    id: UUID
    title: str
    description: str | None
    github_repo_name: str
    project_admin_id: UUID
    created_by: UUID
    modified_by: UUID
    created_at: datetime
    updated_at: datetime
