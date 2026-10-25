from typing import Literal
from uuid import UUID

from api.deps import CurrentUser
from api.v1.schema.issue import IssueOut, IssueSyncOut, IssueSyncRequest
from db.connect import Conn
from fastapi import APIRouter, Query
from services.issue import IssueService

router = APIRouter(prefix="/issue", tags=["issue"])
issue_service = IssueService()


@router.get("", response_model=list[IssueOut])
async def list_issues(
    conn: Conn,
    user: CurrentUser,
    project_id: UUID | None = None,
    state: Literal["open", "closed"] | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return await issue_service.list(
        conn, project_id=project_id, state=state, limit=limit, offset=offset
    )


# Declared before /{issue_id} so "sync" is never read as an id.
@router.post("/sync", response_model=IssueSyncOut)
async def sync_issues(body: IssueSyncRequest, conn: Conn, user: CurrentUser):
    synced = await issue_service.sync(conn, user, body.project_id)
    return IssueSyncOut(project_id=body.project_id, synced=synced)


@router.get("/{issue_id}", response_model=IssueOut)
async def get_issue(issue_id: UUID, conn: Conn, user: CurrentUser):
    return await issue_service.get(conn, issue_id)
