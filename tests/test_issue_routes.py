from api.deps import get_current_user
from api.v1.routes import issue
from main import app


def test_issue_routes_are_registered_in_the_app():
    paths = app.openapi()["paths"]
    assert "get" in paths["/issue"]
    assert "get" in paths["/issue/{issue_id}"]
    assert "post" in paths["/issue/sync"]


def test_sync_is_declared_before_the_id_route():
    paths = [r.path for r in issue.router.routes]
    assert paths.index("/issue/sync") < paths.index("/issue/{issue_id}")


def test_all_issue_routes_require_authentication():
    for route in issue.router.routes:
        deps = {d.call for d in route.dependant.dependencies}
        assert get_current_user in deps, route.path
