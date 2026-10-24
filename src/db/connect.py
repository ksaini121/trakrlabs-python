from collections.abc import AsyncIterator
from typing import Annotated

from config.settings import settings
from fastapi import Depends
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

pool = AsyncConnectionPool(
    settings.database_url,
    min_size=1,
    max_size=10,
    kwargs={"row_factory": dict_row},
    open=False,
)


async def open_pool() -> None:
    await pool.open(wait=True)


async def close_pool() -> None:
    await pool.close()


async def get_conn() -> AsyncIterator[AsyncConnection]:
    # Commits on success, rolls back on exception, then returns the connection to the pool.
    async with pool.connection() as conn:
        yield conn


Conn = Annotated[AsyncConnection, Depends(get_conn)]
