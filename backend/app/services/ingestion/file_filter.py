
from pathlib import PurePosixPath


# Directories that should never be processed
IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".next",
    ".idea",
    ".vscode",
    "site-packages",
}

# Files that should be ignored
IGNORED_FILES = {
    ".DS_Store",
    "Thumbs.db",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
}

# Extensions we don't want to process
IGNORED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".so",
    ".dll",
    ".exe",
    ".bin",
    ".class",
    ".jar",
    ".zip",
    ".tar",
    ".gz",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".mp3",
    ".mp4",
    ".sqlite",
    ".db",
}

# Supported source-code extensions
SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
}


def should_ignore_file(file_path: str) -> bool:
    """
    Return True if a repository file should be excluded.
    """

    path = PurePosixPath(file_path)

    # Ignore files inside excluded directories
    if any(part in IGNORED_DIRECTORIES for part in path.parts):
        return True

    # Ignore specific filenames
    if path.name in IGNORED_FILES:
        return True

    # Ignore unwanted extensions
    if path.suffix.lower() in IGNORED_EXTENSIONS:
        return True

    return False


def is_supported_source_file(file_path: str) -> bool:
    """
    Check whether a file is supported Python, JavaScript,
    TypeScript, or Java source code.
    """

    if should_ignore_file(file_path):
        return False

    path = PurePosixPath(file_path)

    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def filter_repository_files(files: list[dict]) -> list[dict]:
    """
    Filter repository file metadata.

    Returns only supported Python, JavaScript,
    TypeScript, and Java source files.
    """

    return [
        file
        for file in files
        if is_supported_source_file(file["path"])
    ]
