from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock


def issue_payload(**overrides) -> dict:
    payload = {
        "id": 1001,
        "number": 7,
        "title": "Login button broken",
        "body": "Steps to reproduce",
        "state": "open",
        "state_reason": None,
        "html_url": "https://github.com/o/r/issues/7",
        "user": {"login": "alice"},
        "assignees": [{"login": "bob"}, {"login": "carol"}],
        "labels": [{"name": "bug"}, {"name": "p1"}],
        "milestone": {"title": "v1"},
        "comments": 3,
        "created_at": "2026-01-01T10:00:00Z",
        "updated_at": "2026-01-02T10:00:00Z",
        "closed_at": None,
    }
    payload.update(overrides)
    return payload


def fake_pool(conn=None):
    """A pool whose connection() yields the same fake connection each time."""
    conn = conn or AsyncMock()
    pool = MagicMock()

    @asynccontextmanager
    async def connection():
        yield conn

    pool.connection = connection
    pool.conn = conn
    return pool
