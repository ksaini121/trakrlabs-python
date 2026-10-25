from services.github_issues import map_issue
from tests.helpers import issue_payload


def test_maps_all_fields():
    row = map_issue(issue_payload())
    assert row == {
        "github_issue_id": 1001,
        "number": 7,
        "title": "Login button broken",
        "body": "Steps to reproduce",
        "state": "open",
        "state_reason": None,
        "html_url": "https://github.com/o/r/issues/7",
        "author_login": "alice",
        "assignees": ["bob", "carol"],
        "labels": ["bug", "p1"],
        "milestone": "v1",
        "comments_count": 3,
        "github_created_at": "2026-01-01T10:00:00Z",
        "github_updated_at": "2026-01-02T10:00:00Z",
        "github_closed_at": None,
    }


def test_handles_missing_optional_values():
    row = map_issue(
        issue_payload(
            body=None, user=None, milestone=None, assignees=None, labels=None
        )
    )
    assert row["body"] is None
    assert row["author_login"] is None
    assert row["milestone"] is None
    assert row["assignees"] == []
    assert row["labels"] == []


def test_closed_issue_keeps_reason_and_closed_at():
    row = map_issue(
        issue_payload(
            state="closed",
            state_reason="not_planned",
            closed_at="2026-01-03T10:00:00Z",
        )
    )
    assert row["state"] == "closed"
    assert row["state_reason"] == "not_planned"
    assert row["github_closed_at"] == "2026-01-03T10:00:00Z"
