from uuid import UUID

import httpx
from db.queries import issues, projects
from fastapi import HTTPException
from psycopg import AsyncConnection
from services.github_issues import GithubClient, GithubError, GithubIssueSyncService


class IssueService:
    def __init__(
        self, github_client_factory=GithubClient, sync_service=None
    ):
        self._github_client = github_client_factory
        self._sync_service = sync_service or GithubIssueSyncService()

    async def list(
        self,
        conn: AsyncConnection,
        *,
        project_id: UUID | None,
        state: str | None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        return await issues.list_issues(
            conn, project_id=project_id, state=state, limit=limit, offset=offset
        )

    async def get(self, conn: AsyncConnection, issue_id: UUID) -> dict:
        issue = await issues.get_issue_by_id(conn, issue_id)
        if issue is None:
            raise HTTPException(status_code=404, detail="Issue not found")
        return issue

    async def sync(self, conn: AsyncConnection, user: dict, project_id: UUID) -> int:
        """Pull the latest issues for one project from GitHub; returns how many were stored."""
        project = await projects.get_project_by_id(conn, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        if not (user["user_role"] == "admin" or project["project_admin_id"] == user["id"]):
            raise HTTPException(
                status_code=403, detail="Not allowed to sync issues for this project"
            )

        try:
            async with self._github_client() as github:
                return await self._sync_service.sync_project(conn, github, project)
        except GithubError as err:
            if err.status_code in (403, 404):
                raise HTTPException(
                    status_code=422,
                    detail=f"{project['github_repo_name']} not found or not accessible",
                )
            raise HTTPException(status_code=502, detail="GitHub request failed")
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="Could not reach GitHub")
