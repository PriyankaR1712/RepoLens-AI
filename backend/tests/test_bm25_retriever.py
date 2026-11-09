
import pytest
from unittest.mock import Mock

from app.services.retrieval.bm25_retriever import (
    BM25Retriever,
    tokenize_code,
)


def test_tokenize_code_splits_identifiers():
    tokens = tokenize_code("getRepositoryData repository_id")

    assert "get" in tokens
    assert "repository" in tokens
    assert "data" in tokens
    assert "id" in tokens


def test_tokenize_code_handles_empty_input():
    assert tokenize_code("") == []


def test_tokenize_code_handles_non_string_input():
    assert tokenize_code(None) == []


def test_retriever_returns_most_relevant_chunk():
    collection = Mock()
    collection.get.return_value = {
        "ids": ["chunk1", "chunk2"],
        "documents": [
            "def calculate_battery_health(): return battery_health",
            "def load_user_profile(): return user_profile",
        ],
        "metadatas": [
            {"file_path": "battery.py"},
            {"file_path": "users.py"},
        ],
    }

    vector_store = Mock()
    vector_store.get_or_create_collection.return_value = collection

    retriever = BM25Retriever(vector_store)

    results = retriever.retrieve(
        repository_id="repo123",
        query="battery health",
        top_k=2,
    )

    assert len(results) == 1
    assert results[0]["id"] == "chunk1"
    assert results[0]["metadata"]["file_path"] == "battery.py"
    assert results[0]["score"] > 0


def test_retriever_returns_empty_for_no_matching_terms():
    collection = Mock()
    collection.get.return_value = {
        "ids": ["chunk1"],
        "documents": ["def calculate_battery_health(): pass"],
        "metadatas": [{}],
    }

    vector_store = Mock()
    vector_store.get_or_create_collection.return_value = collection

    retriever = BM25Retriever(vector_store)

    results = retriever.retrieve(
        repository_id="repo123",
        query="weather forecast",
    )

    assert results == []


def test_retriever_returns_empty_for_empty_collection():
    collection = Mock()
    collection.get.return_value = {
        "ids": [],
        "documents": [],
        "metadatas": [],
    }

    vector_store = Mock()
    vector_store.get_or_create_collection.return_value = collection

    retriever = BM25Retriever(vector_store)

    assert retriever.retrieve("repo123", "battery") == []


@pytest.mark.parametrize(
    "repository_id, query, top_k",
    [
        ("", "battery", 5),
        ("repo123", "", 5),
        ("repo123", "battery", 0),
        ("repo123", "battery", -1),
        ("repo123", "battery", 1.5),
    ],
)
def test_retriever_rejects_invalid_arguments(
    repository_id,
    query,
    top_k,
):
    retriever = BM25Retriever(Mock())

    with pytest.raises(ValueError):
        retriever.retrieve(repository_id, query, top_k)


def test_retriever_rejects_invalid_bm25_parameters():
    with pytest.raises(ValueError):
        BM25Retriever(Mock(), k1=0)

    with pytest.raises(ValueError):
        BM25Retriever(Mock(), b=1.5)


def test_retriever_respects_top_k():
    collection = Mock()
    collection.get.return_value = {
        "ids": ["chunk1", "chunk2", "chunk3"],
        "documents": [
            "battery health estimation",
            "battery health prediction",
            "battery temperature monitoring",
        ],
        "metadatas": [{}, {}, {}],
    }

    vector_store = Mock()
    vector_store.get_or_create_collection.return_value = collection

    retriever = BM25Retriever(vector_store)

    results = retriever.retrieve(
        "repo123",
        "battery health",
        top_k=1,
    )

    assert len(results) == 1
