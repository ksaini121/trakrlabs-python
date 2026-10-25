from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from config.settings import settings
from core import scheduler
from tests.helpers import fake_pool


def pool_with_lock(locked: bool):
    conn = AsyncMock()
    cursor = MagicMock()
    cursor.fetchone = AsyncMock(return_value={"locked": locked})
    conn.execute.return_value = cursor
    return fake_pool(conn)


@pytest.fixture
def sync_all(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr(scheduler.sync_service, "sync_all", mock)
    return mock


def executed_sql(pool) -> list[str]:
    return [call.args[0] for call in pool.conn.execute.call_args_list]


def test_job_runs_every_configured_interval_without_overlap():
    job = scheduler.create_scheduler().get_job(scheduler.JOB_ID)
    assert job.trigger.interval == timedelta(hours=settings.issue_sync_interval_hours)
    assert job.max_instances == 1
    assert job.coalesce is True


def test_default_interval_is_two_hours():
    assert settings.issue_sync_interval_hours == 2


def test_job_is_scheduled_to_run_at_startup(monkeypatch):
    monkeypatch.setattr(settings, "issue_sync_on_startup", True)
    job = scheduler.create_scheduler().get_job(scheduler.JOB_ID)
    assert job.next_run_time is not None


async def test_skips_sync_when_another_worker_holds_the_lock(monkeypatch, sync_all):
    pool = pool_with_lock(locked=False)
    monkeypatch.setattr(scheduler, "pool", pool)

    await scheduler.run_issue_sync()

    sync_all.assert_not_called()
    assert not any("pg_advisory_unlock" in sql for sql in executed_sql(pool))


async def test_syncs_and_releases_lock(monkeypatch, sync_all):
    pool = pool_with_lock(locked=True)
    monkeypatch.setattr(scheduler, "pool", pool)
    monkeypatch.setattr(scheduler, "GithubClient", MagicMock())

    await scheduler.run_issue_sync()

    sync_all.assert_awaited_once()
    assert "pg_advisory_unlock" in executed_sql(pool)[-1]


async def test_lock_is_released_when_sync_fails(monkeypatch, sync_all):
    sync_all.side_effect = RuntimeError("boom")
    pool = pool_with_lock(locked=True)
    monkeypatch.setattr(scheduler, "pool", pool)
    monkeypatch.setattr(scheduler, "GithubClient", MagicMock())

    with pytest.raises(RuntimeError):
        await scheduler.run_issue_sync()

    assert "pg_advisory_unlock" in executed_sql(pool)[-1]
