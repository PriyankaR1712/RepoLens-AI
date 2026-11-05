
from app.services.ingestion.repository_analyzer import (
    analyze_repository_structure,
)
from app.services.ingestion.source_downloader import (
    download_source_files,
)


def ingest_github_repository(github_url: str) -> dict:
    """
    Run the complete GitHub repository ingestion workflow.

    Steps:
    1. Analyze repository structure.
    2. Filter supported source files.
    3. Detect programming languages.
    4. Download supported source code.
    """

    # Step 1: Analyze repository structure
    analysis = analyze_repository_structure(github_url)

    # Step 2: Check whether supported source files exist
    if not analysis["files"]:
        return {
            "status": "failed",
            "message": "No supported source files found in the repository.",
            "analysis": analysis,
            "download": None,
        }

    # Step 3: Download supported source files
    download = download_source_files(
        github_url=github_url,
        files=analysis["files"],
    )

    # Step 4: Determine ingestion status
    if download["total_downloaded"] == 0:
        status = "failed"
        message = "No source files could be downloaded."
    elif download["total_skipped"] > 0:
        status = "partial"
        message = "Repository ingestion completed with some skipped files."
    else:
        status = "success"
        message = "Repository ingestion completed successfully."

    return {
        "status": status,
        "message": message,
        "repository": analysis["repository"],
        "default_branch": analysis["default_branch"],
        "total_files": analysis["total_files"],
        "supported_source_files": analysis["supported_source_files"],
        "languages": analysis["languages"],
        "downloaded_files": download["total_downloaded"],
        "skipped_files": download["total_skipped"],
        "total_downloaded_bytes": download["total_downloaded_bytes"],
        "files": download["files"],
        "skipped_file_details": download["skipped_files"],
    }
