
import re
from urllib.parse import urlparse
from github import Github, GithubException

def parse_github_url(github_url: str) -> dict:
    """
    Validate a public GitHub repository URL
    and extract its owner and repository name.
    """

    if not github_url or not github_url.strip():
        raise ValueError("GitHub URL cannot be empty")

    parsed_url = urlparse(github_url.strip())

    # Only allow HTTPS GitHub URLs
    if parsed_url.scheme != "https":
        raise ValueError("Only HTTPS GitHub URLs are supported")

    if parsed_url.hostname != "github.com":
        raise ValueError("URL must belong to github.com")

    if parsed_url.username or parsed_url.password:
        raise ValueError("Credentials are not allowed in the URL")

    if parsed_url.port not in (None, 443):
        raise ValueError("Custom ports are not allowed")

    if parsed_url.query or parsed_url.fragment:
        raise ValueError("Query parameters and fragments are not allowed")

    # Extract owner and repository name
    parts = parsed_url.path.strip("/").split("/")

    if len(parts) != 2:
        raise ValueError(
            "URL must contain an owner and repository name"
        )

    owner, repository = parts

    # Remove optional .git suffix
    if repository.endswith(".git"):
        repository = repository[:-4]

    # Validate owner and repository names
    owner_pattern = r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$"
    repository_pattern = r"^[A-Za-z0-9._-]+$"

    if not re.fullmatch(owner_pattern, owner):
        raise ValueError("Invalid GitHub owner name")

    if (
        not re.fullmatch(repository_pattern, repository)
        or repository in {".", ".."}
    ):
        raise ValueError("Invalid GitHub repository name")

    return {
        "owner": owner,
        "repository": repository,
        "url": f"https://github.com/{owner}/{repository}"
    }

def get_github_repository_info(github_url: str) -> dict:
    """
    Retrieve metadata for a public GitHub repository.
    """

    # Validate and extract repository details
    parsed = parse_github_url(github_url)

    try:
        github = Github()
        repository = github.get_repo(
            f"{parsed['owner']}/{parsed['repository']}"
        )

        return {
            "name": repository.name,
            "full_name": repository.full_name,
            "description": repository.description,
            "default_branch": repository.default_branch,
            "language": repository.language,
            "stars": repository.stargazers_count,
            "size_kb": repository.size,
            "html_url": repository.html_url,
            "private": repository.private,
        }

    except GithubException as error:
        if error.status == 404:
            raise ValueError(
                "Repository not found or is not publicly accessible"
            ) from error

        if error.status == 403:
            raise ValueError(
                "GitHub API rate limit exceeded or access forbidden"
            ) from error

        raise ValueError(
            f"GitHub API request failed: {error.data}"
        ) from error

    finally:
        if "github" in locals():
            github.close()
