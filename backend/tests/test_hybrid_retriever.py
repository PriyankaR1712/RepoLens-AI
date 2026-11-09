
import pytest
from unittest.mock import Mock

from app.services.retrieval.hybrid_retriever import HybridRetriever


@pytest.fixture
def dependencies():
    vector_store = Mock()
    embedding_service = Mock()
    bm25_retriever = Mock()

    embedding_service.generate_embeddings.return_value = [
        {"content": "battery health", "embedding": [0.1, 0.2, 0.3]}
    ]

    vector_store.search.return_value = [
        {
            "id": "chunk1",
            "content": "battery health estimation",
            "metadata": {"file_path": "battery.py"},
            "distance": 0.1,
        },
        {
            "id": "chunk2",
            "content": "battery temperature monitoring",
            "metadata": {"file_path": "temperature.py"},
            "distance": 0.2,
        },
    ]

    bm25_retriever.retrieve.return_value = [
        {
            "id": "chunk2",
            "content": "battery temperature monitoring",
            "metadata": {"file_path": "temperature.py"},
            "score": 2.5,
        },
        {
            "id": "chunk3",
            "content": "battery capacity calculation",
            "metadata": {"file_path": "capacity.py"},
            "score": 1.8,
        },
    ]

    retriever = HybridRetriever(
        vector_store=vector_store,
        embedding_service=embedding_service,
        bm25_retriever=bm25_retriever,
    )

    return retriever, vector_store, embedding_service, bm25_retriever


def test_hybrid_retriever_merges_results(dependencies):
    retriever, _, _, _ = dependencies

    results = retriever.retrieve("repo123", "battery health", top_k=5)

    assert len(results) == 3
    assert {result["id"] for result in results} == {
        "chunk1", "chunk2", "chunk3"
    }


def test_hybrid_retriever_removes_duplicates(dependencies):
    retriever, _, _, _ = dependencies

    results = retriever.retrieve("repo123", "battery health")

    ids = [result["id"] for result in results]

    assert len(ids) == len(set(ids))


def test_hybrid_retriever_fuses_rankings(dependencies):
    retriever, _, _, _ = dependencies

    results = retriever.retrieve("repo123", "battery health")

    # chunk2 appears in both retrieval lists.
    assert results[0]["id"] == "chunk2"
    assert results[0]["semantic_distance"] == 0.2
    assert results[0]["bm25_score"] == 2.5
    assert results[0]["rrf_score"] > results[1]["rrf_score"]


def test_hybrid_retriever_respects_top_k(dependencies):
    retriever, _, _, _ = dependencies

    results = retriever.retrieve("repo123", "battery health", top_k=2)

    assert len(results) == 2


def test_hybrid_retriever_assigns_final_ranks(dependencies):
    retriever, _, _, _ = dependencies

    results = retriever.retrieve("repo123", "battery health")

    assert [result["rank"] for result in results] == [1, 2, 3]


def test_hybrid_retriever_handles_empty_results(dependencies):
    retriever, vector_store, _, bm25_retriever = dependencies

    vector_store.search.return_value = []
    bm25_retriever.retrieve.return_value = []

    results = retriever.retrieve("repo123", "battery health")

    assert results == []


def test_hybrid_retriever_uses_candidate_multiplier(dependencies):
    retriever, vector_store, _, bm25_retriever = dependencies

    retriever.retrieve("repo123", "battery health", top_k=5)

    vector_store.search.assert_called_once()
    bm25_retriever.retrieve.assert_called_once()

    assert vector_store.search.call_args.kwargs["top_k"] == 15
    assert bm25_retriever.retrieve.call_args.kwargs["top_k"] == 15


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
def test_hybrid_retriever_rejects_invalid_arguments(
    dependencies, repository_id, query, top_k
):
    retriever, _, _, _ = dependencies

    with pytest.raises(ValueError):
        retriever.retrieve(repository_id, query, top_k)


def test_hybrid_retriever_rejects_invalid_rrf_parameter():
    with pytest.raises(ValueError):
        HybridRetriever(
            Mock(),
            Mock(),
            rrf_k=0,
        )


def test_hybrid_retriever_rejects_invalid_embedding(dependencies):
    retriever, _, embedding_service, _ = dependencies

    embedding_service.generate_embeddings.return_value = []

    with pytest.raises(ValueError, match="invalid result"):
        retriever.retrieve("repo123", "battery health")
