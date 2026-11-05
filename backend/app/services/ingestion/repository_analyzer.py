
from app.services.ingestion.github_contents import (
    get_repository_file_structure,
)
from app.services.ingestion.file_filter import (
    filter_repository_files,
)
from app.services.ingestion.language_detector import (
    detect_languages,
)


def analyze_repository_structure(github_url: str) -> dict:
    """
    Discover repository files, filter supported source files,
    and identify supported and unsupported languages.
    """

    # Fetch repository structure from GitHub
    repository_data = get_repository_file_structure(github_url)

    all_files = repository_data["files"]

    # Filter supported source files
    supported_files = filter_repository_files(all_files)

    # Detect languages across the repository
    language_info = detect_languages(all_files)

    return {
        "repository": repository_data["repository"],
        "default_branch": repository_data["default_branch"],
        "total_files": len(all_files),
        "supported_source_files": len(supported_files),
        "languages": language_info,
        "files": supported_files,
    }
