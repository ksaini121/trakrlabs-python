from uuid import UUID

from psycopg import AsyncConnection

UPSERT_USER = """
    INSERT INTO users (github_id, username, email, avatar_url)
    VALUES (%(github_id)s, %(username)s, %(email)s, %(avatar_url)s)
    ON CONFLICT (github_id) DO UPDATE SET
        username   = EXCLUDED.username,
        email      = COALESCE(EXCLUDED.email, users.email),
        avatar_url = EXCLUDED.avatar_url,
        updated_at = now()
    RETURNING *
"""


GET_USER_BY_ID = "SELECT * FROM users WHERE id = %s"


async def get_user_by_id(conn: AsyncConnection, user_id: UUID) -> dict | None:
    cur = await conn.execute(GET_USER_BY_ID, (user_id,))
    return await cur.fetchone()


async def upsert_user(
    conn: AsyncConnection,
    *,
    github_id: int,
    username: str,
    email: str | None,
    avatar_url: str | None,
) -> dict:
    cur = await conn.execute(
        UPSERT_USER,
        {
            "github_id": github_id,
            "username": username,
            "email": email,
            "avatar_url": avatar_url,
        },
    )
    return await cur.fetchone()
