
import base64
from unittest.mock import patch, MagicMock

from app.services.ingestion.source_downloader import (
    download_source_files,
    MAX_FILE_SIZE_BYTES,
)


GITHUB_URL = "https://github.com/PriyankaR1712/RepoLens-AI"


def create_mock_github():
    """Create a mocked GitHub client and repository."""

    mock_github = MagicMock()
    mock_repository = MagicMock()

    mock_repository.full_name = "PriyankaR1712/RepoLens-AI"
    mock_github.get_repo.return_value = mock_repository

    return mock_github, mock_repository


@patch("app.services.ingestion.source_downloader.Github")
def test_download_source_file_success(mock_github_class):
    mock_github, mock_repository = create_mock_github()
    mock_github_class.return_value = mock_github

    source_code = "print('Hello RepoLens!')"
    encoded_content = base64.b64encode(
        source_code.encode("utf-8")
    ).decode("utf-8")

    mock_blob = MagicMock()
    mock_blob.content = encoded_content

    mock_repository.get_git_blob.return_value = mock_blob

    files = [
        {
            "path": "main.py",
            "size": len(source_code),
            "sha": "abc123",
        }
    ]

    result = download_source_files(GITHUB_URL, files)

    assert result["total_downloaded"] == 1
    assert result["total_skipped"] == 0
    assert result["files"][0]["content"] == source_code
    assert result["files"][0]["path"] == "main.py"
    assert result["total_downloaded_bytes"] == len(
        source_code.encode("utf-8")
    )

    mock_github.close.assert_called_once()


@patch("app.services.ingestion.source_downloader.Github")
def test_skip_oversized_file(mock_github_class):
    mock_github, mock_repository = create_mock_github()
    mock_github_class.return_value = mock_github

    files = [
        {
            "path": "large.py",
            "size": MAX_FILE_SIZE_BYTES + 1,
            "sha": "large123",
        }
    ]

    result = download_source_files(GITHUB_URL, files)

    assert result["total_downloaded"] == 0
    assert result["total_skipped"] == 1
    assert "size limit" in result["skipped_files"][0]["reason"]

    mock_repository.get_git_blob.assert_not_called()


@patch("app.services.ingestion.source_downloader.Github")
def test_skip_invalid_utf8_file(mock_github_class):
    mock_github, mock_repository = create_mock_github()
    mock_github_class.return_value = mock_github

    invalid_content = b"\xff\xfe\xfa"
    encoded_content = base64.b64encode(
        invalid_content
    ).decode("utf-8")

    mock_blob = MagicMock()
    mock_blob.content = encoded_content

    mock_repository.get_git_blob.return_value = mock_blob

    files = [
        {
            "path": "invalid.py",
            "size": len(invalid_content),
            "sha": "invalid123",
        }
    ]

    result = download_source_files(GITHUB_URL, files)

    assert result["total_downloaded"] == 0
    assert result["total_skipped"] == 1
    assert result["skipped_files"][0]["reason"] == (
        "File is not valid UTF-8 text"
    )


@patch("app.services.ingestion.source_downloader.Github")
def test_skip_unsupported_file(mock_github_class):
    mock_github, mock_repository = create_mock_github()
    mock_github_class.return_value = mock_github

    files = [
        {
            "path": "image.png",
            "size": 100,
            "sha": "image123",
        }
    ]

    result = download_source_files(GITHUB_URL, files)

    assert result["total_downloaded"] == 0
    assert result["total_skipped"] == 1
    assert result["skipped_files"][0]["reason"] == (
        "Unsupported file type"
    )

    mock_repository.get_git_blob.assert_not_called()
