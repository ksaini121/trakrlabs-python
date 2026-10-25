from datetime import datetime, timezone

import httpx
import pytest
from config.settings import settings
from services.github_issues import GithubClient, GithubError, GithubRateLimited


def client_for(handler) -> GithubClient:
    return GithubClient(transport=httpx.MockTransport(handler))


async def collect(client, repo="o/r", since=None):
    return [page async for page in client.iter_issues(repo, since)]


async def test_sends_pat_and_issue_query_params():
    seen = []

    def handler(request: httpx.Request):
        seen.append(request)
        return httpx.Response(200, json=[])

    since = datetime(2026, 1, 1, tzinfo=timezone.utc)
    async with client_for(handler) as client:
        await collect(client, since=since)

    request = seen[0]
    assert request.headers["authorization"] == f"Bearer {settings.github_project_pat}"
    assert request.url.path == "/repos/o/r/issues"
    params = request.url.params
    assert params["state"] == "all"
    assert params["sort"] == "updated"
    assert params["direction"] == "asc"
    assert params["per_page"] == "100"
    assert params["since"] == since.isoformat()


async def test_no_since_param_on_first_sync():
    seen = []

    def handler(request: httpx.Request):
        seen.append(request)
        return httpx.Response(200, json=[])

    async with client_for(handler) as client:
        await collect(client)
    assert "since" not in seen[0].url.params


async def test_follows_next_link_until_exhausted():
    def handler(request: httpx.Request):
        if request.url.params.get("page") == "2":
            return httpx.Response(200, json=[{"id": 2}])
        return httpx.Response(
            200,
            json=[{"id": 1}],
            headers={
                "Link": '<https://api.github.com/repos/o/r/issues?page=2>; rel="next"'
            },
        )

    async with client_for(handler) as client:
        pages = await collect(client)
    assert pages == [[{"id": 1}], [{"id": 2}]]


@pytest.mark.parametrize("status", [401, 403, 404, 500])
async def test_error_statuses_raise_github_error(status):
    async with client_for(lambda r: httpx.Response(status, text="nope")) as client:
        with pytest.raises(GithubError) as exc:
            await collect(client)
    assert exc.value.status_code == status
    assert not isinstance(exc.value, GithubRateLimited)


async def test_429_is_rate_limited():
    async with client_for(lambda r: httpx.Response(429)) as client:
        with pytest.raises(GithubRateLimited):
            await collect(client)


async def test_403_with_exhausted_quota_is_rate_limited():
    response = httpx.Response(403, headers={"x-ratelimit-remaining": "0"})
    async with client_for(lambda r: response) as client:
        with pytest.raises(GithubRateLimited):
            await collect(client)


async def test_get_repo_returns_json_and_raises_on_404():
    def handler(request: httpx.Request):
        if request.url.path == "/repos/o/r":
            return httpx.Response(200, json={"full_name": "o/r"})
        return httpx.Response(404)

    async with client_for(handler) as client:
        assert (await client.get_repo("o/r"))["full_name"] == "o/r"
        with pytest.raises(GithubError):
            await client.get_repo("o/missing")
