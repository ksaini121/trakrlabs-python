from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from db.queries import issues, projects
from fastapi import HTTPException
from services.github_issues import GithubError
from services.issue import IssueService

ADMIN_ID = uuid4()
USER = {"id": ADMIN_ID, "user_role": "user"}
SITE_ADMIN = {"id": uuid4(), "user_role": "admin"}
PROJECT = {"id": uuid4(), "project_admin_id": ADMIN_ID, "github_repo_name": "o/r"}


class FakeGithub:
    def __call__(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None


@pytest.fixture
def sync_service():
    return AsyncMock(sync_project=AsyncMock(return_value=4))


@pytest.fixture
def service(sync_service, monkeypatch):
    monkeypatch.setattr(
        projects, "get_project_by_id", AsyncMock(return_value=PROJECT)
    )
    return IssueService(FakeGithub(), sync_service)


async def test_get_returns_issue(monkeypatch):
    issue = {"id": uuid4()}
    monkeypatch.setattr(issues, "get_issue_by_id", AsyncMock(return_value=issue))
    assert await IssueService().get(None, issue["id"]) == issue


async def test_get_missing_issue_is_404(monkeypatch):
    monkeypatch.setattr(issues, "get_issue_by_id", AsyncMock(return_value=None))
    with pytest.raises(HTTPException) as exc:
        await IssueService().get(None, uuid4())
    assert exc.value.status_code == 404


async def test_list_passes_filters_through(monkeypatch):
    mock = AsyncMock(return_value=[])
    monkeypatch.setattr(issues, "list_issues", mock)
    pid = uuid4()

    await IssueService().list(None, project_id=pid, state="open", limit=10, offset=5)

    mock.assert_awaited_once_with(
        None, project_id=pid, state="open", limit=10, offset=5
    )


@pytest.mark.parametrize("user", [USER, SITE_ADMIN])
async def test_project_admin_and_site_admin_can_sync(service, sync_service, user):
    assert await service.sync(None, user, PROJECT["id"]) == 4
    sync_service.sync_project.assert_awaited_once()
    assert sync_service.sync_project.await_args.args[2] == PROJECT


async def test_other_users_cannot_sync(service, sync_service):
    other = {"id": uuid4(), "user_role": "user"}
    with pytest.raises(HTTPException) as exc:
        await service.sync(None, other, PROJECT["id"])
    assert exc.value.status_code == 403
    sync_service.sync_project.assert_not_called()


async def test_sync_unknown_project_is_404(service, monkeypatch):
    monkeypatch.setattr(projects, "get_project_by_id", AsyncMock(return_value=None))
    with pytest.raises(HTTPException) as exc:
        await service.sync(None, USER, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.parametrize(
    "error,status",
    [
        (GithubError(404, "x"), 422),
        (GithubError(403, "x"), 422),
        (GithubError(500, "x"), 502),
        (GithubError(401, "x"), 502),
        (httpx.ConnectError("down"), 502),
    ],
)
async def test_github_failures_map_to_http_errors(
    service, sync_service, error, status
):
    sync_service.sync_project.side_effect = error
    with pytest.raises(HTTPException) as exc:
        await service.sync(None, USER, PROJECT["id"])
    assert exc.value.status_code == status
