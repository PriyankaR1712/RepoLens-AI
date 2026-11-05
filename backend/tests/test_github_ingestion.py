
from unittest.mock import patch

from app.services.ingestion.github_ingestion import (
    ingest_github_repository,
)


GITHUB_URL = "https://github.com/PriyankaR1712/RepoLens-AI"


def mock_analysis():
    return {
        "repository": "PriyankaR1712/RepoLens-AI",
        "default_branch": "main",
        "total_files": 13,
        "supported_source_files": 2,
        "languages": {
            "detected_languages": ["Python"],
            "supported_languages": ["Python"],
            "unsupported_languages": [],
            "has_supported_code": True,
        },
        "files": [
            {"path": "main.py", "size": 100, "sha": "abc123"},
            {"path": "utils.py", "size": 200, "sha": "def456"},
        ],
    }


def mock_download():
    return {
        "repository": "PriyankaR1712/RepoLens-AI",
        "total_downloaded": 2,
        "total_skipped": 0,
        "total_downloaded_bytes": 300,
        "files": [
            {"path": "main.py", "content": "print('Hello')"},
            {"path": "utils.py", "content": "def add(a, b): return a + b"},
        ],
        "skipped_files": [],
    }


@patch("app.services.ingestion.github_ingestion.download_source_files")
@patch("app.services.ingestion.github_ingestion.analyze_repository_structure")
def test_successful_ingestion(mock_analyze, mock_download_files):
    mock_analyze.return_value = mock_analysis()
    mock_download_files.return_value = mock_download()

    result = ingest_github_repository(GITHUB_URL)

    assert result["status"] == "success"
    assert result["downloaded_files"] == 2
    assert result["skipped_files"] == 0
    assert result["total_downloaded_bytes"] == 300

    mock_analyze.assert_called_once_with(GITHUB_URL)
    mock_download_files.assert_called_once()


@patch("app.services.ingestion.github_ingestion.download_source_files")
@patch("app.services.ingestion.github_ingestion.analyze_repository_structure")
def test_ingestion_with_no_supported_files(
    mock_analyze,
    mock_download_files,
):
    analysis = mock_analysis()
    analysis["files"] = []
    analysis["supported_source_files"] = 0

    mock_analyze.return_value = analysis

    result = ingest_github_repository(GITHUB_URL)

    assert result["status"] == "failed"
    assert result["download"] is None
    assert "No supported source files" in result["message"]

    mock_download_files.assert_not_called()


@patch("app.services.ingestion.github_ingestion.download_source_files")
@patch("app.services.ingestion.github_ingestion.analyze_repository_structure")
def test_partial_ingestion(
    mock_analyze,
    mock_download_files,
):
    mock_analyze.return_value = mock_analysis()

    download = mock_download()
    download["total_downloaded"] = 1
    download["total_skipped"] = 1
    download["skipped_files"] = [
        {
            "path": "utils.py",
            "reason": "File is not valid UTF-8 text",
        }
    ]

    mock_download_files.return_value = download

    result = ingest_github_repository(GITHUB_URL)

    assert result["status"] == "partial"
    assert result["downloaded_files"] == 1
    assert result["skipped_files"] == 1
    assert len(result["skipped_file_details"]) == 1


@patch("app.services.ingestion.github_ingestion.download_source_files")
@patch("app.services.ingestion.github_ingestion.analyze_repository_structure")
def test_ingestion_when_all_downloads_fail(
    mock_analyze,
    mock_download_files,
):
    mock_analyze.return_value = mock_analysis()

    download = mock_download()
    download["total_downloaded"] = 0
    download["total_skipped"] = 2
    download["total_downloaded_bytes"] = 0
    download["files"] = []

    mock_download_files.return_value = download

    result = ingest_github_repository(GITHUB_URL)

    assert result["status"] == "failed"
    assert result["downloaded_files"] == 0
    assert result["skipped_files"] == 2
    assert result["message"] == "No source files could be downloaded."

