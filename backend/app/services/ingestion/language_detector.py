
from pathlib import PurePosixPath

from app.services.ingestion.file_filter import (
    IGNORED_DIRECTORIES,
    IGNORED_FILES,
)


LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".cpp": "C++",
    ".cc": "C++",
    ".c": "C",
    ".h": "C/C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".dart": "Dart",
    ".html": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
}

SUPPORTED_LANGUAGES = {
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
}


def detect_languages(files: list[dict]) -> dict:
    """
    Detect programming languages present in a repository.

    Returns supported and unsupported languages separately.
    """

    detected = set()

    for file in files:
        path = PurePosixPath(file["path"])

        # Ignore files inside excluded directories
        if any(part in IGNORED_DIRECTORIES for part in path.parts):
            continue

        if path.name in IGNORED_FILES:
            continue

        language = LANGUAGE_EXTENSIONS.get(path.suffix.lower())

        if language:
            detected.add(language)

    detected_languages = sorted(detected)

    supported = sorted(
        language
        for language in detected
        if language in SUPPORTED_LANGUAGES
    )

    unsupported = sorted(
        language
        for language in detected
        if language not in SUPPORTED_LANGUAGES
    )

    return {
        "detected_languages": detected_languages,
        "supported_languages": supported,
        "unsupported_languages": unsupported,
        "has_supported_code": bool(supported),
    }
