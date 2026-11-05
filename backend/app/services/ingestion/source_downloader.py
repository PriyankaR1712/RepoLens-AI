import base64
from github import Github, GithubException

from app.services.ingestion.github import parse_github_url
from app.services.ingestion.file_filter import (
    is_supported_source_file,
)


# Maximum size allowed for an individual source file: 1 MB
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024

# Maximum total source code downloaded per repository: 20 MB
MAX_TOTAL_SIZE_BYTES = 20 * 1024 * 1024


def download_source_files(
    github_url: str,
    files: list[dict],
) -> dict:
    """
    Download supported source files from a public GitHub repository.

    Preserves original file paths and skips files that are too large,
    inaccessible, or cannot be decoded as UTF-8.
    """

    parsed = parse_github_url(github_url)

    github = Github()

    downloaded_files = []
    skipped_files = []
    total_downloaded_bytes = 0

    try:
        repository = github.get_repo(
            f"{parsed['owner']}/{parsed['repository']}"
        )

        for file in files:

            file_path = file["path"]
            file_size = file.get("size")

            # Ignore unsupported files
            if not is_supported_source_file(file_path):
                skipped_files.append({
                    "path": file_path,
                    "reason": "Unsupported file type"
                })
                continue

            # Check individual file size
            if file_size is None or file_size > MAX_FILE_SIZE_BYTES:
                skipped_files.append({
                    "path": file_path,
                    "reason": "File exceeds size limit or size is unknown"
                })
                continue

            # Check total download limit
            if total_downloaded_bytes + file_size > MAX_TOTAL_SIZE_BYTES:
                skipped_files.append({
                    "path": file_path,
                    "reason": "Repository download limit reached"
                })
                continue

            try:
                # Retrieve the Git blob using its SHA
                blob = repository.get_git_blob(file["sha"])

                # Decode Base64 content into bytes
                content_bytes = base64.b64decode(blob.content)

                # Verify actual individual file size
                if len(content_bytes) > MAX_FILE_SIZE_BYTES:
                    skipped_files.append({
                        "path": file_path,
                        "reason": "Downloaded content exceeds size limit"
                    })
                    continue

                # Verify actual total repository download size
                if total_downloaded_bytes + len(content_bytes) > MAX_TOTAL_SIZE_BYTES:
                    skipped_files.append({
                        "path": file_path,
                        "reason": "Repository download limit reached"
                    })
                    continue

                # Convert source code into text
                content = content_bytes.decode("utf-8")

                downloaded_files.append({
                    "path": file_path,
                    "size": len(content_bytes),
                    "sha": file["sha"],
                    "content": content
                })

                total_downloaded_bytes += len(content_bytes)

            except UnicodeDecodeError:
                skipped_files.append({
                    "path": file_path,
                    "reason": "File is not valid UTF-8 text"
                })

            except GithubException as error:
                skipped_files.append({
                    "path": file_path,
                    "reason": f"GitHub API error: {error.status}"
                })

        return {
            "repository": repository.full_name,
            "total_downloaded": len(downloaded_files),
            "total_skipped": len(skipped_files),
            "total_downloaded_bytes": total_downloaded_bytes,
            "files": downloaded_files,
            "skipped_files": skipped_files
        }

    finally:
        github.close()
