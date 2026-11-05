
from github import Github, GithubException

from app.services.ingestion.github import parse_github_url


def get_repository_file_structure(github_url: str) -> dict:
    """
    Retrieve the file structure of a public GitHub repository.

    Returns file paths and metadata without downloading file contents.
    """

    parsed = parse_github_url(github_url)
    github = Github()

    try:
        repository = github.get_repo(
            f"{parsed['owner']}/{parsed['repository']}"
        )

        # Retrieve the complete Git tree recursively
        tree = repository.get_git_tree(
            sha=repository.default_branch,
            recursive=True
        )

        # GitHub may truncate very large recursive trees
        if tree.truncated:
            raise ValueError(
                "Repository is too large to retrieve its complete "
                "file structure in one request."
            )

        files = []

        for item in tree.tree:
            # Include actual files, not directories or submodules
            if item.type != "blob":
                continue

            files.append({
                "path": item.path,
                "size": item.size,
                "sha": item.sha,
                "type": "file"
            })

        return {
            "repository": repository.full_name,
            "default_branch": repository.default_branch,
            "total_files": len(files),
            "files": files
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
        github.close()
