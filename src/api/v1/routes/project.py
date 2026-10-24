from datetime import datetime
from uuid import UUID

from api.deps import CurrentUser
from db.connect import Conn
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from services.project import ProjectService

router = APIRouter(prefix="/project", tags=["project"])
project_service = ProjectService()


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = None
    github_repo_name: str = Field(min_length=1)
    # Defaults to the creator when omitted.
    project_admin_id: UUID | None = None


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    github_repo_name: str | None = Field(default=None, min_length=1)
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


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(body: ProjectCreate, conn: Conn, user: CurrentUser):
    return await project_service.create(conn, user, **body.model_dump())


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    conn: Conn,
    user: CurrentUser,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return await project_service.list(conn, limit=limit, offset=offset)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: UUID, conn: Conn, user: CurrentUser):
    return await project_service.get(conn, project_id)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: UUID, body: ProjectUpdate, conn: Conn, user: CurrentUser
):
    return await project_service.update(
        conn, user, project_id, body.model_dump(exclude_unset=True)
    )


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: UUID, conn: Conn, user: CurrentUser):
    await project_service.delete(conn, user, project_id)
