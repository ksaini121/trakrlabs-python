from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from db.queries import projects, users
from fastapi import HTTPException
from services.github_issues import GithubError
from services.project import ProjectService

USER = {"id": uuid4(), "user_role": "user"}


class FakeGithub:
    def __init__(self, error=None):
        self.error = error
        self.checked = []

    def __call__(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None

    async def get_repo(self, repo):
        self.checked.append(repo)
        if self.error:
            raise self.error
        return {"full_name": repo}


@pytest.fixture
def db(monkeypatch):
    mocks = {
        "get_user": AsyncMock(return_value={"id": USER["id"]}),
        "create": AsyncMock(return_value={"id": uuid4()}),
        "get_project": AsyncMock(),
        "update": AsyncMock(return_value={"id": uuid4()}),
    }
    monkeypatch.setattr(users, "get_user_by_id", mocks["get_user"])
    monkeypatch.setattr(projects, "create_project", mocks["create"])
    monkeypatch.setattr(projects, "get_project_by_id", mocks["get_project"])
    monkeypatch.setattr(projects, "update_project", mocks["update"])
    return mocks


def existing_project(repo="o/old"):
    return {"id": uuid4(), "project_admin_id": USER["id"], "github_repo_name": repo}


async def create(service):
    return await service.create(
        None,
        USER,
        title="t",
        description=None,
        github_repo_name="o/r",
        project_admin_id=None,
    )


async def test_create_checks_repo_then_inserts(db):
    github = FakeGithub()
    await create(ProjectService(github))
    assert github.checked == ["o/r"]
    db["create"].assert_awaited_once()


@pytest.mark.parametrize("status", [403, 404])
async def test_create_unreachable_repo_is_422(db, status):
    service = ProjectService(FakeGithub(GithubError(status, "nope")))
    with pytest.raises(HTTPException) as exc:
        await create(service)
    assert exc.value.status_code == 422
    db["create"].assert_not_called()


@pytest.mark.parametrize(
    "error", [GithubError(401, "bad pat"), GithubError(500, "x"), httpx.ConnectError("")]
)
async def test_create_github_failure_is_502(db, error):
    with pytest.raises(HTTPException) as exc:
        await create(ProjectService(FakeGithub(error)))
    assert exc.value.status_code == 502
    db["create"].assert_not_called()


async def test_update_checks_repo_only_when_it_changes(db):
    project = existing_project("o/old")
    db["get_project"].return_value = project
    github = FakeGithub()
    service = ProjectService(github)

    await service.update(None, USER, project["id"], {"github_repo_name": "o/old"})
    assert github.checked == []

    await service.update(None, USER, project["id"], {"github_repo_name": "o/new"})
    assert github.checked == ["o/new"]


async def test_update_without_repo_skips_github(db):
    project = existing_project()
    db["get_project"].return_value = project
    github = FakeGithub()

    await ProjectService(github).update(None, USER, project["id"], {"title": "x"})

    assert github.checked == []
    db["update"].assert_awaited_once()


async def test_update_unreachable_repo_is_422_and_not_saved(db):
    project = existing_project()
    db["get_project"].return_value = project
    service = ProjectService(FakeGithub(GithubError(404, "nope")))

    with pytest.raises(HTTPException) as exc:
        await service.update(None, USER, project["id"], {"github_repo_name": "o/x"})

    assert exc.value.status_code == 422
    db["update"].assert_not_called()


async def test_update_still_enforces_permissions_and_nulls(db):
    project = {**existing_project(), "project_admin_id": uuid4()}
    db["get_project"].return_value = project
    service = ProjectService(FakeGithub())

    with pytest.raises(HTTPException) as exc:
        await service.update(None, USER, project["id"], {"title": "x"})
    assert exc.value.status_code == 403

    db["get_project"].return_value = existing_project()
    with pytest.raises(HTTPException) as exc:
        await service.update(None, USER, project["id"], {"title": None})
    assert exc.value.status_code == 422
