from datetime import datetime
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

UPSERT_ISSUE = """
    INSERT INTO issues (
        project_id, github_issue_id, number, title, body, state, state_reason,
        html_url, author_login, assignees, labels, milestone, comments_count,
        github_created_at, github_updated_at, github_closed_at
    )
    VALUES (
        %(project_id)s, %(github_issue_id)s, %(number)s, %(title)s, %(body)s,
        %(state)s, %(state_reason)s, %(html_url)s, %(author_login)s,
        %(assignees)s, %(labels)s, %(milestone)s, %(comments_count)s,
        %(github_created_at)s, %(github_updated_at)s, %(github_closed_at)s
    )
    ON CONFLICT (project_id, github_issue_id) DO UPDATE SET
        number            = EXCLUDED.number,
        title             = EXCLUDED.title,
        body              = EXCLUDED.body,
        state             = EXCLUDED.state,
        state_reason      = EXCLUDED.state_reason,
        html_url          = EXCLUDED.html_url,
        author_login      = EXCLUDED.author_login,
        assignees         = EXCLUDED.assignees,
        labels            = EXCLUDED.labels,
        milestone         = EXCLUDED.milestone,
        comments_count    = EXCLUDED.comments_count,
        github_created_at = EXCLUDED.github_created_at,
        github_updated_at = EXCLUDED.github_updated_at,
        github_closed_at  = EXCLUDED.github_closed_at,
        synced_at         = now(),
        updated_at        = now()
"""

GET_LATEST_UPDATED_AT = """
    SELECT max(github_updated_at) AS latest FROM issues WHERE project_id = %s
"""


async def upsert_issues(
    conn: AsyncConnection, project_id: UUID, rows: list[dict]
) -> None:
    if not rows:
        return
    params = [
        {
            **row,
            "project_id": project_id,
            "assignees": Jsonb(row["assignees"]),
            "labels": Jsonb(row["labels"]),
        }
        for row in rows
    ]
    async with conn.cursor() as cur:
        await cur.executemany(UPSERT_ISSUE, params)


async def get_latest_updated_at(
    conn: AsyncConnection, project_id: UUID
) -> datetime | None:
    cur = await conn.execute(GET_LATEST_UPDATED_AT, (project_id,))
    row = await cur.fetchone()
    return row["latest"] if row else None


GET_ISSUE_BY_ID = "SELECT * FROM issues WHERE id = %s"

LIST_ISSUES = """
    SELECT * FROM issues
    WHERE (%(project_id)s::uuid IS NULL OR project_id = %(project_id)s)
      AND (%(state)s::text IS NULL OR state = %(state)s)
    ORDER BY github_updated_at DESC
    LIMIT %(limit)s OFFSET %(offset)s
"""


async def get_issue_by_id(conn: AsyncConnection, issue_id: UUID) -> dict | None:
    cur = await conn.execute(GET_ISSUE_BY_ID, (issue_id,))
    return await cur.fetchone()


async def list_issues(
    conn: AsyncConnection,
    *,
    project_id: UUID | None,
    state: str | None,
    limit: int,
    offset: int,
) -> list[dict]:
    cur = await conn.execute(
        LIST_ISSUES,
        {"project_id": project_id, "state": state, "limit": limit, "offset": offset},
    )
    return await cur.fetchall()
