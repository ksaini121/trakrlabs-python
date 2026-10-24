from uuid import UUID

from psycopg import AsyncConnection

CREATE_PROJECT = """
    INSERT INTO projects (
        title, description, github_repo_name,
        project_admin_id, created_by, modified_by
    )
    VALUES (
        %(title)s, %(description)s, %(github_repo_name)s,
        %(project_admin_id)s, %(user_id)s, %(user_id)s
    )
    RETURNING *
"""

GET_PROJECT_BY_ID = "SELECT * FROM projects WHERE id = %s"

LIST_PROJECTS = """
    SELECT * FROM projects
    ORDER BY created_at DESC
    LIMIT %s OFFSET %s
"""

DELETE_PROJECT = "DELETE FROM projects WHERE id = %s"

# Columns a caller may change via update_project; keys outside this set are rejected.
UPDATABLE_FIELDS = frozenset(
    {"title", "description", "github_repo_name", "project_admin_id"}
)


async def create_project(
    conn: AsyncConnection,
    *,
    title: str,
    description: str | None,
    github_repo_name: str,
    project_admin_id: UUID,
    user_id: UUID,
) -> dict:
    cur = await conn.execute(
        CREATE_PROJECT,
        {
            "title": title,
            "description": description,
            "github_repo_name": github_repo_name,
            "project_admin_id": project_admin_id,
            "user_id": user_id,
        },
    )
    return await cur.fetchone()


async def get_project_by_id(conn: AsyncConnection, project_id: UUID) -> dict | None:
    cur = await conn.execute(GET_PROJECT_BY_ID, (project_id,))
    return await cur.fetchone()


async def list_projects(
    conn: AsyncConnection, *, limit: int = 50, offset: int = 0
) -> list[dict]:
    cur = await conn.execute(LIST_PROJECTS, (limit, offset))
    return await cur.fetchall()


async def update_project(
    conn: AsyncConnection,
    project_id: UUID,
    *,
    user_id: UUID,
    **fields,
) -> dict | None:
    """Partially update a project; only the given fields change (None clears a nullable one)."""
    unknown = fields.keys() - UPDATABLE_FIELDS
    if unknown:
        raise ValueError(f"Cannot update fields: {sorted(unknown)}")

    assignments = [f"{name} = %({name})s" for name in fields]
    assignments += ["modified_by = %(user_id)s", "updated_at = now()"]
    query = f"UPDATE projects SET {', '.join(assignments)} WHERE id = %(id)s RETURNING *"

    cur = await conn.execute(query, {**fields, "user_id": user_id, "id": project_id})
    return await cur.fetchone()


async def delete_project(conn: AsyncConnection, project_id: UUID) -> bool:
    cur = await conn.execute(DELETE_PROJECT, (project_id,))
    return cur.rowcount > 0
