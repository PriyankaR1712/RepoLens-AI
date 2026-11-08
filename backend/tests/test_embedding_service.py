
import numpy as np
import pytest

from app.services.embeddings.embedding_service import (
    EmbeddingService,
    get_embedding_service,
)


class FakeEmbeddingModel:
    """Mock model that returns predictable normalized embeddings."""

    def __init__(self):
        self.received_texts = []
        self.encode_calls = 0

    def encode(
        self,
        texts,
        batch_size,
        show_progress_bar,
        convert_to_numpy,
        normalize_embeddings,
    ):
        self.received_texts.extend(texts)
        self.encode_calls += 1

        assert show_progress_bar is False
        assert convert_to_numpy is True
        assert normalize_embeddings is True

        return np.array([
            [0.6, 0.8] for _ in texts
        ])


@pytest.fixture
def service_with_mock_model():
    service = EmbeddingService(batch_size=2)
    mock_model = FakeEmbeddingModel()
    service._model = mock_model

    return service, mock_model


def test_generate_embeddings_for_code_chunks(
    service_with_mock_model,
):
    service, mock_model = service_with_mock_model

    chunks = [
        {
            "file_path": "app/main.py",
            "language": "Python",
            "symbol_name": "calculate_total",
            "symbol_type": "function",
            "parent_class": None,
            "start_line": 1,
            "end_line": 5,
            "content": "def calculate_total():\n    return 100",
            "chunk_index": 0,
        }
    ]

    results = service.generate_embeddings(chunks)

    assert len(results) == 1
    assert results[0]["file_path"] == "app/main.py"
    assert results[0]["symbol_name"] == "calculate_total"
    assert results[0]["content"] == chunks[0]["content"]
    assert results[0]["embedding"] == [0.6, 0.8]
    assert mock_model.encode_calls == 1


def test_generate_embeddings_for_multiple_chunks(
    service_with_mock_model,
):
    service, mock_model = service_with_mock_model

    chunks = [
        {"content": "def first(): pass", "chunk_index": 0},
        {"content": "def second(): pass", "chunk_index": 1},
    ]

    results = service.generate_embeddings(chunks)

    assert len(results) == 2
    assert all("embedding" in chunk for chunk in results)
    assert mock_model.received_texts == [
        "def first(): pass",
        "def second(): pass",
    ]


def test_empty_chunks_return_empty_list(
    service_with_mock_model,
):
    service, mock_model = service_with_mock_model

    assert service.generate_embeddings([]) == []
    assert mock_model.encode_calls == 0


def test_chunk_without_content_is_rejected(
    service_with_mock_model,
):
    service, _ = service_with_mock_model

    with pytest.raises(ValueError):
        service.generate_embeddings([{"file_path": "main.py"}])


def test_chunk_with_empty_content_is_rejected(
    service_with_mock_model,
):
    service, _ = service_with_mock_model

    with pytest.raises(ValueError):
        service.generate_embeddings([{"content": "   "}])


def test_invalid_chunk_type_is_rejected(
    service_with_mock_model,
):
    service, _ = service_with_mock_model

    with pytest.raises(TypeError):
        service.generate_embeddings(["not a dictionary"])


def test_invalid_batch_size_is_rejected():
    with pytest.raises(ValueError):
        EmbeddingService(batch_size=0)


def test_embedding_service_singleton():
    get_embedding_service.cache_clear()

    first = get_embedding_service()
    second = get_embedding_service()

    assert first is second

    get_embedding_service.cache_clear()
