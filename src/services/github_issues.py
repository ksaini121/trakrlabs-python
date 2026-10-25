import logging
import re
from collections.abc import AsyncIterator
from datetime import datetime

import httpx
from config.settings import settings
from db.queries import issues, projects
from psycopg import AsyncConnection

logger = logging.getLogger("uvicorn.error")

REPO_NAME_REGEX = r"^[\w.-]+/[\w.-]+$"
REPO_NAME_PATTERN = re.compile(REPO_NAME_REGEX)


class GithubError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(f"GitHub returned {status_code}: {message}")
        self.status_code = status_code
        self.message = message


class GithubRateLimited(GithubError):
    """The PAT's rate limit is used up; every other call in this run would fail too."""


class GithubClient:
    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None):
        self._http = httpx.AsyncClient(
            base_url=settings.github_base_url,
            headers={
                "Authorization": f"Bearer {settings.github_project_pat}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30,
            transport=transport,
        )

    async def __aenter__(self) -> "GithubClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self._http.aclose()

    async def get_repo(self, repo: str) -> dict:
        resp = await self._http.get(f"/repos/{repo}")
        self._raise_for_error(resp)
        return resp.json()

    async def iter_issues(
        self, repo: str, since: datetime | None = None
    ) -> AsyncIterator[list[dict]]:
        """Yield one page of issues at a time, oldest update first, following Link headers."""
        params = {
            "state": "all",
            "sort": "updated",
            "direction": "asc",
            "per_page": 100,
        }
        if since is not None:
            params["since"] = since.isoformat()

        url: str | None = f"/repos/{repo}/issues"
        while url:
            resp = await self._http.get(url, params=params)
            self._raise_for_error(resp)
            yield resp.json()
            # The next link already carries the query string.
            url = resp.links.get("next", {}).get("url")
            params = None

    @staticmethod
    def _raise_for_error(resp: httpx.Response) -> None:
        if resp.status_code < 400:
            return
        message = resp.text[:200]
        if resp.status_code == 429 or (
            resp.status_code == 403 and resp.headers.get("x-ratelimit-remaining") == "0"
        ):
            raise GithubRateLimited(resp.status_code, message)
        raise GithubError(resp.status_code, message)


def map_issue(payload: dict) -> dict:
    """Turn a GitHub issue payload into the column values of the issues table."""
    milestone = payload.get("milestone")
    author = payload.get("user")
    return {
        "github_issue_id": payload["id"],
        "number": payload["number"],
        "title": payload["title"],
        "body": payload.get("body"),
        "state": payload["state"],
        "state_reason": payload.get("state_reason"),
        "html_url": payload["html_url"],
        "author_login": author["login"] if author else None,
        "assignees": [a["login"] for a in payload.get("assignees") or []],
        "labels": [label["name"] for label in payload.get("labels") or []],
        "milestone": milestone["title"] if milestone else None,
        "comments_count": payload.get("comments", 0),
        "github_created_at": payload["created_at"],
        "github_updated_at": payload["updated_at"],
        "github_closed_at": payload.get("closed_at"),
    }


class GithubIssueSyncService:
    async def sync_project(
        self, conn: AsyncConnection, client: GithubClient, project: dict
    ) -> int:
        """Fetch issues changed since the last sync and upsert them; returns how many were stored."""
        repo = project["github_repo_name"]
        if not REPO_NAME_PATTERN.match(repo):
            logger.warning(
                "Skipping project %s: %r is not in owner/repo form", project["id"], repo
            )
            return 0

        since = await issues.get_latest_updated_at(conn, project["id"])
        count = 0
        async for page in client.iter_issues(repo, since):
            # The issues endpoint also returns pull requests.
            rows = [map_issue(item) for item in page if "pull_request" not in item]
            await issues.upsert_issues(conn, project["id"], rows)
            count += len(rows)
        return count

    async def sync_all(self, pool, client: GithubClient) -> None:
        """Sync every project, each in its own transaction so one failure does not affect the rest."""
        async with pool.connection() as conn:
            all_projects = await projects.list_all_projects(conn)

        for project in all_projects:
            repo = project["github_repo_name"]
            try:
                async with pool.connection() as conn:
                    count = await self.sync_project(conn, client, project)
                logger.info("Synced %d issue(s) for %s", count, repo)
            except GithubRateLimited as err:
                logger.error("GitHub rate limit hit, ending this sync run: %s", err)
                return
            except (GithubError, httpx.HTTPError) as err:
                logger.error("Issue sync failed for %s: %s", repo, err)
            except Exception:
                logger.exception("Unexpected error syncing %s", repo)
