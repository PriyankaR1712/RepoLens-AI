
import pytest

from app.services.ingestion.file_filter import (
    should_ignore_file,
    is_supported_source_file,
    filter_repository_files,
)


@pytest.mark.parametrize(
    "file_path",
    [
        "main.py",
        "src/app.js",
        "components/Button.jsx",
        "src/index.ts",
        "src/App.tsx",
        "src/Main.java",
    ],
)
def test_supported_source_files(file_path):
    assert is_supported_source_file(file_path) is True


@pytest.mark.parametrize(
    "file_path",
    [
        ".git/config",
        ".venv/lib/python.py",
        "node_modules/package/index.js",
        "build/output.py",
        "src/__pycache__/main.py",
        "package-lock.json",
        "assets/image.png",
        "docs/manual.pdf",
        "backend/app.exe",
        "src/Main.class",
    ],
)
def test_ignored_files(file_path):
    assert should_ignore_file(file_path) is True
    assert is_supported_source_file(file_path) is False


def test_filter_repository_files():
    files = [
        {"path": "main.py", "size": 100},
        {"path": "app.js", "size": 200},
        {"path": "Main.java", "size": 300},
        {"path": "image.png", "size": 400},
        {"path": "node_modules/package/index.js", "size": 500},
        {"path": "README.md", "size": 600},
    ]

    result = filter_repository_files(files)

    result_paths = [file["path"] for file in result]

    assert result_paths == [
        "main.py",
        "app.js",
        "Main.java",
    ]
    assert len(result) == 3
