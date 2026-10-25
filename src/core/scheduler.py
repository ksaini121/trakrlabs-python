import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config.settings import settings
from db.connect import pool
from services.github_issues import GithubClient, GithubIssueSyncService

logger = logging.getLogger("uvicorn.error")

# Arbitrary constant that identifies the issue sync in pg_try_advisory_lock.
ISSUE_SYNC_LOCK_ID = 727301
JOB_ID = "sync_github_issues"

sync_service = GithubIssueSyncService()


async def run_issue_sync() -> None:
    """Sync issues unless another worker already is; the advisory lock spans workers."""
    async with pool.connection() as lock_conn:
        cur = await lock_conn.execute(
            "SELECT pg_try_advisory_lock(%s) AS locked", (ISSUE_SYNC_LOCK_ID,)
        )
        if not (await cur.fetchone())["locked"]:
            logger.info("Issue sync already running in another worker, skipping")
            return
        try:
            async with GithubClient() as client:
                await sync_service.sync_all(pool, client)
        finally:
            await lock_conn.execute(
                "SELECT pg_advisory_unlock(%s)", (ISSUE_SYNC_LOCK_ID,)
            )


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    job_options = {}
    if settings.issue_sync_on_startup:
        # Passing next_run_time=None would pause the job, so only set it when wanted.
        job_options["next_run_time"] = datetime.now(timezone.utc)
    scheduler.add_job(
        run_issue_sync,
        "interval",
        hours=settings.issue_sync_interval_hours,
        id=JOB_ID,
        max_instances=1,
        coalesce=True,
        **job_options,
    )
    return scheduler
