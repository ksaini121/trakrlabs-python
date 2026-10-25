from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest
from db.queries import issues, projects
from services.github_issues import (
    GithubError,
    GithubIssueSyncService,
    GithubRateLimited,
)
from tests.helpers import fake_pool, issue_payload


class FakeClient:
    """Stands in for GithubClient; `pages` maps repo -> pages or an exception to raise."""

    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    async def iter_issues(self, repo, since=None):
        self.calls.append((repo, since))
        result = self.pages[repo]
        if isinstance(result, Exception):
            raise result
        for page in result:
            yield page


def project(repo="o/r"):
    return {"id": uuid4(), "github_repo_name": repo}


@pytest.fixture
def upserts(monkeypatch):
    calls = []

    async def fake_upsert(conn, project_id, rows):
        calls.append((project_id, rows))

    async def fake_latest(conn, project_id):
        return None

    monkeypatch.setattr(issues, "upsert_issues", fake_upsert)
    monkeypatch.setattr(issues, "get_latest_updated_at", fake_latest)
    return calls


async def test_upserts_mapped_rows_with_project_id(upserts):
    proj = project()
    client = FakeClient({"o/r": [[issue_payload(id=1), issue_payload(id=2)]]})

    count = await GithubIssueSyncService().sync_project(None, client, proj)

    assert count == 2
    project_id, rows = upserts[0]
    assert project_id == proj["id"]
    assert [r["github_issue_id"] for r in rows] == [1, 2]
    assert rows[0]["labels"] == ["bug", "p1"]


async def test_pull_requests_are_filtered_out(upserts):
    page = [issue_payload(id=1), issue_payload(id=2, pull_request={"url": "x"})]
    client = FakeClient({"o/r": [page]})

    count = await GithubIssueSyncService().sync_project(None, client, project())

    assert count == 1
    assert [r["github_issue_id"] for r in upserts[0][1]] == [1]


async def test_every_page_is_stored(upserts):
    client = FakeClient({"o/r": [[issue_payload(id=1)], [issue_payload(id=2)]]})
    count = await GithubIssueSyncService().sync_project(None, client, project())
    assert count == 2
    assert len(upserts) == 2


async def test_watermark_is_passed_as_since(monkeypatch, upserts):
    watermark = datetime(2026, 1, 2, tzinfo=timezone.utc)

    async def fake_latest(conn, project_id):
        return watermark

    monkeypatch.setattr(issues, "get_latest_updated_at", fake_latest)
    client = FakeClient({"o/r": [[]]})

    await GithubIssueSyncService().sync_project(None, client, project())

    assert client.calls == [("o/r", watermark)]


@pytest.mark.parametrize("bad", ["repo", "a/b/c", "", "owner/"])
async def test_invalid_repo_name_is_skipped(upserts, bad):
    client = FakeClient({})
    count = await GithubIssueSyncService().sync_project(None, client, project(bad))
    assert count == 0
    assert client.calls == []
    assert upserts == []


@pytest.fixture
def synced(monkeypatch, upserts):
    """Run sync_all over the given projects and return the repos that reached upsert."""

    async def run(project_list, pages):
        async def fake_list(conn):
            return project_list

        monkeypatch.setattr(projects, "list_all_projects", fake_list)
        await GithubIssueSyncService().sync_all(fake_pool(), FakeClient(pages))
        by_id = {p["id"]: p["github_repo_name"] for p in project_list}
        return [by_id[project_id] for project_id, _ in upserts]

    return run


async def test_one_failing_project_does_not_stop_the_others(synced):
    projs = [project("o/bad"), project("o/net"), project("o/good")]
    pages = {
        "o/bad": GithubError(404, "missing"),
        "o/net": httpx.ConnectError("down"),
        "o/good": [[issue_payload()]],
    }
    assert await synced(projs, pages) == ["o/good"]


async def test_unexpected_error_does_not_stop_the_others(synced):
    projs = [project("o/boom"), project("o/good")]
    pages = {"o/boom": RuntimeError("bug"), "o/good": [[issue_payload()]]}
    assert await synced(projs, pages) == ["o/good"]


async def test_rate_limit_ends_the_whole_run(synced):
    projs = [project("o/limited"), project("o/never")]
    pages = {
        "o/limited": GithubRateLimited(429, "slow down"),
        "o/never": [[issue_payload()]],
    }
    assert await synced(projs, pages) == []
