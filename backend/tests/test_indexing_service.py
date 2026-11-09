
from unittest.mock import Mock

import pytest

from app.services.retrieval.indexing_service import (
    IndexingService,
    parse_source_file,
)


@pytest.fixture
def mock_embedding_service():
    service = Mock()
    service.generate_embeddings.side_effect = lambda chunks: [
        {**chunk, "embedding": [0.1, 0.2, 0.3]}
        for chunk in chunks
    ]
    return service


@pytest.fixture
def mock_vector_store():
    store = Mock()
    store.add_chunks.side_effect = lambda repository_id, chunks: len(chunks)
    store.sync_chunks.side_effect = lambda repository_id, chunks: len(chunks)
    return store


@pytest.fixture
def indexing_service(mock_vector_store, mock_embedding_service):
    return IndexingService(
        vector_store=mock_vector_store,
        embedding_service=mock_embedding_service,
    )


def test_parse_source_file_selects_python_parser(monkeypatch):
    import app.services.retrieval.indexing_service as module

    expected = {"status": "success", "language": "Python"}

    monkeypatch.setattr(
        module,
        "parse_python_file",
        lambda source, path: expected,
    )

    result = parse_source_file("def hello(): pass", "hello.py")

    assert result is expected


@pytest.mark.parametrize(
    ("file_path", "expected_language"),
    [
        ("app.js", "JavaScript"),
        ("app.jsx", "JavaScript"),
        ("app.ts", "TypeScript"),
        ("app.tsx", "TSX"),
        ("Main.java", "Java"),
    ],
)
def test_parse_source_file_selects_tree_sitter_language(
    monkeypatch,
    file_path,
    expected_language,
):
    import app.services.retrieval.indexing_service as module

    def fake_parser(source_code, language, file_path=""):
        return {
            "status": "success",
            "language": language,
            "file_path": file_path,
        }

    monkeypatch.setattr(
        module,
        "parse_tree_sitter_file",
        fake_parser,
    )

    result = parse_source_file("sample code", file_path)

    assert result["language"] == expected_language
    assert result["file_path"] == file_path


def test_parse_source_file_rejects_unsupported_extension():
    result = parse_source_file("sample", "readme.md")

    assert result["status"] == "failed"
    assert result["symbols"] == []


def test_index_repository_with_python_file(
    indexing_service,
    mock_vector_store,
    mock_embedding_service,
):
    ingestion_result = {
        "status": "success",
        "files": [
            {
                "path": "main.py",
                "content": "def greet():\n    return 'Hello'",
            }
        ],
    }

    result = indexing_service.index_repository(
        ingestion_result,
        "owner/repository",
    )

    assert result["status"] == "success"
    assert result["processed_files"] == 1
    assert result["failed_files"] == 0
    assert result["total_symbols"] == 1
    assert result["total_chunks"] == 1
    assert result["indexed_chunks"] == 1

    mock_embedding_service.generate_embeddings.assert_called_once()
    mock_vector_store.sync_chunks.assert_called_once()


def test_index_repository_preserves_file_without_symbols(
    indexing_service,
    mock_vector_store,
):
    ingestion_result = {
        "status": "success",
        "files": [
            {
                "path": "config.py",
                "content": "APP_NAME = 'RepoLens'\nDEBUG = True",
            }
        ],
    }

    result = indexing_service.index_repository(
        ingestion_result,
        "owner/repository",
    )

    assert result["processed_files"] == 1
    assert result["total_symbols"] == 0
    assert result["total_chunks"] == 1
    assert result["indexed_chunks"] == 1

    stored_chunks = mock_vector_store.sync_chunks.call_args.args[1]

    assert stored_chunks[0]["symbol_type"] == "file"
    assert "APP_NAME" in stored_chunks[0]["content"]


def test_index_repository_handles_partial_parser_result(
    indexing_service,
):
    ingestion_result = {
        "status": "success",
        "files": [
            {
                "path": "partial.py",
                "content": "def greet():\n    return 'Hello'",
            }
        ],
    }

    import app.services.retrieval.indexing_service as module

    original_parser = module.parse_python_file

    def partial_parser(source_code, file_path):
        parsed = original_parser(source_code, file_path)
        parsed["status"] = "partial"
        parsed["error"] = {
            "message": "Partial parsing warning.",
            "line": 1,
            "column": 1,
        }
        return parsed

    module.parse_python_file = partial_parser

    try:
        result = indexing_service.index_repository(
            ingestion_result,
            "owner/repository",
        )
    finally:
        module.parse_python_file = original_parser

    assert result["status"] == "partial"
    assert result["processed_files"] == 1
    assert result["failed_files"] == 0
    assert result["total_chunks"] == 1
    assert result["indexed_chunks"] == 1
    assert result["errors"][0]["message"] == "Partial parsing warning."


def test_index_repository_skips_failed_parser_result(
    indexing_service,
    mock_embedding_service,
):
    import app.services.retrieval.indexing_service as module

    monkeypatch_result = {
        "status": "failed",
        "language": "Python",
        "file_path": "broken.py",
        "total_symbols": 0,
        "symbols": [],
        "error": {"message": "Syntax error"},
    }

    original_parser = module.parse_python_file
    module.parse_python_file = lambda source, path: monkeypatch_result

    try:
        result = indexing_service.index_repository(
            {
                "status": "success",
                "files": [
                    {"path": "broken.py", "content": "invalid code"}
                ],
            },
            "owner/repository",
        )
    finally:
        module.parse_python_file = original_parser

    assert result["status"] == "partial"
    assert result["processed_files"] == 0
    assert result["failed_files"] == 1
    assert result["total_chunks"] == 0
    mock_embedding_service.generate_embeddings.assert_not_called()


def test_index_repository_handles_empty_repository(indexing_service):
    result = indexing_service.index_repository(
        {"status": "success", "files": []},
        "owner/repository",
    )

    assert result["status"] == "success"
    assert result["total_files"] == 0
    assert result["total_chunks"] == 0
    assert result["indexed_chunks"] == 0


@pytest.mark.parametrize(
    "ingestion_result",
    [
        None,
        {},
        {"status": "failed", "files": []},
        {"status": "success", "files": "invalid"},
    ],
)
def test_index_repository_rejects_invalid_ingestion(
    indexing_service,
    ingestion_result,
):
    with pytest.raises(ValueError):
        indexing_service.index_repository(
            ingestion_result,
            "owner/repository",
        )


def test_index_repository_rejects_empty_repository_id(indexing_service):
    with pytest.raises(ValueError):
        indexing_service.index_repository(
            {"status": "success", "files": []},
            "",
        )


def test_index_repository_reports_invalid_file_content(indexing_service):
    result = indexing_service.index_repository(
        {
            "status": "success",
            "files": [
                {"path": "broken.py", "content": None}
            ],
        },
        "owner/repository",
    )

    assert result["status"] == "partial"
    assert result["failed_files"] == 1
    assert result["errors"][0]["file_path"] == "broken.py"


def test_index_repository_handles_embedding_failure(
    mock_vector_store,
    mock_embedding_service,
):
    mock_embedding_service.generate_embeddings.side_effect = (
        RuntimeError("Embedding model unavailable.")
    )

    service = IndexingService(
        vector_store=mock_vector_store,
        embedding_service=mock_embedding_service,
    )

    result = service.index_repository(
        {
            "status": "success",
            "files": [
                {
                    "path": "main.py",
                    "content": "def greet():\n    return 'Hello'",
                }
            ],
        },
        "owner/repository",
    )

    assert result["status"] == "failed"
    assert result["total_chunks"] == 1
    assert result["indexed_chunks"] == 0
    assert result["errors"][-1]["stage"] == "embedding"
    mock_vector_store.add_chunks.assert_not_called()


def test_index_repository_handles_storage_failure(
    mock_vector_store,
    mock_embedding_service,
):
    mock_vector_store.sync_chunks.side_effect = RuntimeError(
        "ChromaDB unavailable."
    )

    service = IndexingService(
        vector_store=mock_vector_store,
        embedding_service=mock_embedding_service,
    )

    result = service.index_repository(
        {
            "status": "success",
            "files": [
                {
                    "path": "main.py",
                    "content": "def greet():\n    return 'Hello'",
                }
            ],
        },
        "owner/repository",
    )

    assert result["status"] == "failed"
    assert result["errors"][-1]["stage"] == "storage"
    assert result["indexed_chunks"] == 0


def test_index_repository_rejects_malformed_file_entry(
    indexing_service,
):
    result = indexing_service.index_repository(
        {
            "status": "success",
            "files": [
                None,
                {
                    "path": "valid.py",
                    "content": "def greet():\n    return 'Hello'",
                },
            ],
        },
        "owner/repository",
    )

    assert result["status"] == "partial"
    assert result["total_files"] == 2
    assert result["failed_files"] == 1
    assert result["processed_files"] == 1
    assert result["indexed_chunks"] == 1


def test_index_repository_preserves_partial_ingestion_status(
    indexing_service,
):
    result = indexing_service.index_repository(
        {
            "status": "partial",
            "files": [],
        },
        "owner/repository",
    )

    assert result["status"] == "partial"


def test_index_repository_rejects_invalid_embedding_output(
    mock_vector_store,
    mock_embedding_service,
):
    mock_embedding_service.generate_embeddings.side_effect = None
    mock_embedding_service.generate_embeddings.return_value = []

    service = IndexingService(
        vector_store=mock_vector_store,
        embedding_service=mock_embedding_service,
    )

    result = service.index_repository(
        {
            "status": "success",
            "files": [
                {
                    "path": "main.py",
                    "content": "def greet():\n    return 'Hello'",
                }
            ],
        },
        "owner/repository",
    )

    assert result["status"] == "failed"
    assert result["errors"][-1]["stage"] == "embedding"
    mock_vector_store.add_chunks.assert_not_called()

def test_partial_indexing_does_not_synchronize(
    indexing_service,
    mock_vector_store,
):
    result = indexing_service.index_repository(
        {
            "status": "partial",
            "files": [
                {
                    "path": "main.py",
                    "content": "def greet():\n    return 'Hello'",
                }
            ],
        },
        "owner/repository",
    )

    assert result["status"] == "partial"
    mock_vector_store.add_chunks.assert_called_once()
    mock_vector_store.sync_chunks.assert_not_called()


def test_failed_file_does_not_trigger_synchronization(
    indexing_service,
    mock_vector_store,
    monkeypatch,
):
    import app.services.retrieval.indexing_service as module

    monkeypatch.setattr(
        module,
        "parse_python_file",
        lambda source, path: {
            "status": "failed",
            "language": "Python",
            "file_path": path,
            "total_symbols": 0,
            "symbols": [],
            "error": {"message": "Syntax error"},
        },
    )

    result = indexing_service.index_repository(
        {
            "status": "success",
            "files": [
                {
                    "path": "broken.py",
                    "content": "invalid code",
                }
            ],
        },
        "owner/repository",
    )

    assert result["status"] == "partial"
    mock_vector_store.sync_chunks.assert_not_called()
    mock_vector_store.add_chunks.assert_not_called()


def test_successful_empty_repository_synchronizes(
    indexing_service,
    mock_vector_store,
):
    result = indexing_service.index_repository(
        {
            "status": "success",
            "files": [],
        },
        "owner/repository",
    )

    assert result["status"] == "success"
    mock_vector_store.sync_chunks.assert_called_once_with(
        "owner/repository",
        [],
    )
    mock_vector_store.add_chunks.assert_not_called()
