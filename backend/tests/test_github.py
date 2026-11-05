
import pytest

from app.services.ingestion.github import parse_github_url


def test_parse_valid_github_url():
    result = parse_github_url(
        "https://github.com/PriyankaR1712/RepoLens-AI"
    )

    assert result["owner"] == "PriyankaR1712"
    assert result["repository"] == "RepoLens-AI"


def test_parse_github_url_with_git_extension():
    result = parse_github_url(
        "https://github.com/PriyankaR1712/RepoLens-AI.git"
    )

    assert result["repository"] == "RepoLens-AI"


@pytest.mark.parametrize(
    "url",
    [
        "https://google.com/user/repo",
        "not-a-url",
        "https://github.com/user",
        "http://github.com/user/repo",
        "https://github.com/user/repo?tab=readme",
    ],
)
def test_invalid_github_urls(url):
    with pytest.raises(ValueError):
        parse_github_url(url)
