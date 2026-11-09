
import numpy as np
import pytest
from unittest.mock import Mock

from app.services.retrieval.cross_encoder_reranker import (
    CrossEncoderReranker,
)


@pytest.fixture
def mock_model():
    model = Mock()
    model.predict.return_value = np.array([0.2, 0.9, 0.5])
    return model


@pytest.fixture
def reranker(mock_model):
    return CrossEncoderReranker(model=mock_model)


@pytest.fixture
def documents():
    return [
        {"id": "chunk1", "content": "temperature monitoring"},
        {"id": "chunk2", "content": "battery health estimation"},
        {"id": "chunk3", "content": "capacity calculation"},
    ]


def test_reranker_sorts_by_score(reranker, documents):
    results = reranker.rerank("battery health", documents)

    assert [item["id"] for item in results] == [
        "chunk2", "chunk3", "chunk1"
    ]


def test_reranker_adds_scores(reranker, documents):
    results = reranker.rerank("battery health", documents)

    assert results[0]["rerank_score"] == 0.9
    assert results[1]["rerank_score"] == 0.5
    assert results[2]["rerank_score"] == 0.2


def test_reranker_assigns_ranks(reranker, documents):
    results = reranker.rerank("battery health", documents)

    assert [item["rank"] for item in results] == [1, 2, 3]


def test_reranker_respects_top_k(reranker, documents):
    results = reranker.rerank(
        "battery health",
        documents,
        top_k=2,
    )

    assert len(results) == 2


def test_reranker_preserves_original_metadata(
    mock_model, reranker
):
    mock_model.predict.return_value = np.array([0.9])

    documents = [
        {
            "id": "chunk1",
            "content": "battery health",
            "metadata": {"file_path": "battery.py"},
            "rrf_score": 0.04,
        }
    ]

    results = reranker.rerank("battery health", documents)

    assert results[0]["metadata"]["file_path"] == "battery.py"
    assert results[0]["rrf_score"] == 0.04

def test_reranker_does_not_modify_original_documents(
    reranker, documents
):
    original = [document.copy() for document in documents]

    reranker.rerank("battery health", documents)

    assert documents == original


def test_reranker_handles_empty_documents(reranker):
    assert reranker.rerank("battery health", []) == []


def test_reranker_rejects_empty_query(reranker, documents):
    with pytest.raises(ValueError):
        reranker.rerank("", documents)


def test_reranker_rejects_invalid_top_k(reranker, documents):
    with pytest.raises(ValueError):
        reranker.rerank("battery health", documents, top_k=0)


def test_reranker_rejects_non_list_documents(reranker):
    with pytest.raises(ValueError):
        reranker.rerank("battery health", None)


def test_reranker_rejects_invalid_document(reranker):
    with pytest.raises(ValueError):
        reranker.rerank(
            "battery health",
            [{"id": "chunk1"}],
        )


def test_reranker_rejects_invalid_score_count(
    mock_model, documents
):
    mock_model.predict.return_value = np.array([0.5])

    reranker = CrossEncoderReranker(model=mock_model)

    with pytest.raises(ValueError, match="unexpected number"):
        reranker.rerank("battery health", documents)


def test_reranker_rejects_non_finite_scores(
    mock_model, documents
):
    mock_model.predict.return_value = np.array([
        0.2, float("nan"), 0.5
    ])

    reranker = CrossEncoderReranker(model=mock_model)

    with pytest.raises(ValueError, match="non-finite"):
        reranker.rerank("battery health", documents)


def test_reranker_passes_query_document_pairs(
    reranker, mock_model, documents
):
    reranker.rerank("battery health", documents)

    mock_model.predict.assert_called_once_with([
        ("battery health", "temperature monitoring"),
        ("battery health", "battery health estimation"),
        ("battery health", "capacity calculation"),
    ])


def test_reranker_loads_model_lazily():
    reranker = CrossEncoderReranker()

    assert reranker._model is None


def test_reranker_rejects_invalid_model_name():
    with pytest.raises(ValueError):
        CrossEncoderReranker(model_name="")
