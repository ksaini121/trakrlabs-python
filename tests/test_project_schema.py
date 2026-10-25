import pytest
from api.v1.schema.project import ProjectCreate, ProjectUpdate
from pydantic import ValidationError


@pytest.mark.parametrize("repo", ["Therapz-Inc/TherapzWebapp", "a/b", "o.rg/re_po-1"])
def test_accepts_owner_slash_repo(repo):
    assert ProjectCreate(title="t", github_repo_name=repo).github_repo_name == repo
    assert ProjectUpdate(github_repo_name=repo).github_repo_name == repo


@pytest.mark.parametrize("repo", ["repo", "a/b/c", "", "owner/", "/repo", "a b/c"])
def test_rejects_other_repo_names(repo):
    with pytest.raises(ValidationError):
        ProjectCreate(title="t", github_repo_name=repo)
    with pytest.raises(ValidationError):
        ProjectUpdate(github_repo_name=repo)


def test_update_repo_name_is_optional():
    assert ProjectUpdate().model_dump(exclude_unset=True) == {}
