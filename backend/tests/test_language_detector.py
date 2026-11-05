
import pytest

from app.services.ingestion.language_detector import detect_languages


def test_detect_single_supported_language():
    files = [
        {"path": "main.py"},
        {"path": "utils.py"},
    ]

    result = detect_languages(files)

    assert result["detected_languages"] == ["Python"]
    assert result["supported_languages"] == ["Python"]
    assert result["unsupported_languages"] == []
    assert result["has_supported_code"] is True


def test_detect_multiple_supported_languages():
    files = [
        {"path": "main.py"},
        {"path": "app.js"},
        {"path": "App.tsx"},
        {"path": "Main.java"},
    ]

    result = detect_languages(files)

    assert result["detected_languages"] == [
        "Java",
        "JavaScript",
        "Python",
        "TypeScript",
    ]
    assert result["supported_languages"] == [
        "Java",
        "JavaScript",
        "Python",
        "TypeScript",
    ]
    assert result["unsupported_languages"] == []
    assert result["has_supported_code"] is True


def test_detect_unsupported_languages():
    files = [
        {"path": "main.cpp"},
        {"path": "server.go"},
        {"path": "script.rs"},
    ]

    result = detect_languages(files)

    assert result["detected_languages"] == [
        "C++",
        "Go",
        "Rust",
    ]
    assert result["supported_languages"] == []
    assert result["unsupported_languages"] == [
        "C++",
        "Go",
        "Rust",
    ]
    assert result["has_supported_code"] is False


def test_detect_mixed_supported_and_unsupported_languages():
    files = [
        {"path": "main.py"},
        {"path": "app.js"},
        {"path": "server.go"},
        {"path": "Main.java"},
    ]

    result = detect_languages(files)

    assert result["supported_languages"] == [
        "Java",
        "JavaScript",
        "Python",
    ]
    assert result["unsupported_languages"] == ["Go"]
    assert result["has_supported_code"] is True


def test_ignore_excluded_directories():
    files = [
        {"path": "main.py"},
        {"path": "node_modules/package/index.js"},
        {"path": ".venv/lib/example.py"},
        {"path": "build/generated.cpp"},
    ]

    result = detect_languages(files)

    assert result["detected_languages"] == ["Python"]


def test_ignore_excluded_filenames():
    files = [
        {"path": "main.py"},
        {"path": "package-lock.json"},
        {"path": "Thumbs.db"},
    ]

    result = detect_languages(files)

    assert result["detected_languages"] == ["Python"]


def test_no_programming_languages_detected():
    files = [
        {"path": "README.md"},
        {"path": "docs/manual.pdf"},
        {"path": "assets/image.png"},
    ]

    result = detect_languages(files)

    assert result["detected_languages"] == []
    assert result["supported_languages"] == []
    assert result["unsupported_languages"] == []
    assert result["has_supported_code"] is False
