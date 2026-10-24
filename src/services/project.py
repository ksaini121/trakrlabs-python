from uuid import UUID

from db.queries import projects, users
from fastapi import HTTPException
from psycopg import AsyncConnection
from psycopg.errors import ForeignKeyViolation

# Only description is nullable in the database.
NULLABLE_FIELDS = frozenset({"description"})


class ProjectService:
    async def create(
        self,
        conn: AsyncConnection,
        user: dict,
        *,
        title: str,
        description: str | None,
        github_repo_name: str,
        project_admin_id: UUID | None,
    ) -> dict:
        """Create a project; the creator becomes its admin unless another user is given."""
        admin_id = project_admin_id or user["id"]
        await self._ensure_user_exists(conn, admin_id)
        return await projects.create_project(
            conn,
            title=title,
            description=description,
            github_repo_name=github_repo_name,
            project_admin_id=admin_id,
            user_id=user["id"],
        )

    async def list(
        self, conn: AsyncConnection, *, limit: int, offset: int
    ) -> list[dict]:
        return await projects.list_projects(conn, limit=limit, offset=offset)

    async def get(self, conn: AsyncConnection, project_id: UUID) -> dict:
        project = await projects.get_project_by_id(conn, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    async def update(
        self, conn: AsyncConnection, user: dict, project_id: UUID, fields: dict
    ) -> dict:
        """Apply a partial update; only the project admin or a site admin may do so."""
        project = await self.get(conn, project_id)
        if not self._can_manage(user, project):
            raise HTTPException(
                status_code=403, detail="Not allowed to modify this project"
            )

        for name, value in fields.items():
            if value is None and name not in NULLABLE_FIELDS:
                raise HTTPException(status_code=422, detail=f"{name} cannot be null")
        if fields.get("project_admin_id"):
            await self._ensure_user_exists(conn, fields["project_admin_id"])

        updated = await projects.update_project(
            conn, project_id, user_id=user["id"], **fields
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return updated

    async def delete(self, conn: AsyncConnection, user: dict, project_id: UUID) -> None:
        """Delete a project; only the project admin or a site admin may do so."""
        project = await self.get(conn, project_id)
        if not self._can_manage(user, project):
            raise HTTPException(
                status_code=403, detail="Not allowed to delete this project"
            )
        try:
            await projects.delete_project(conn, project_id)
        except ForeignKeyViolation:
            raise HTTPException(
                status_code=409, detail="Project is referenced by other records"
            )

    def _can_manage(self, user: dict, project: dict) -> bool:
        return user["user_role"] == "admin" or project["project_admin_id"] == user["id"]

    async def _ensure_user_exists(self, conn: AsyncConnection, user_id: UUID) -> None:
        if await users.get_user_by_id(conn, user_id) is None:
            raise HTTPException(
                status_code=422, detail="project_admin_id: user not found"
            )
