
from app.services.retrieval.vector_store import VectorStore
from app.services.retrieval.bm25_retriever import BM25Retriever
from app.services.retrieval.hybrid_retriever import HybridRetriever
from app.services.retrieval.cross_encoder_reranker import CrossEncoderReranker


class FakeEmbeddingService:
    """Provide deterministic query embeddings for integration testing."""

    def generate_embeddings(self, chunks):
        return [
            {
                **chunk,
                "embedding": [0.1, 0.2, 0.3],
            }
            for chunk in chunks
        ]


def test_hybrid_retrieval_with_real_chromadb(tmp_path):
    vector_store = VectorStore(
        persist_directory=str(tmp_path / "chroma")
    )

    repository_id = "hybrid-integration-test"

    chunks = [
        {
            "file_path": "battery.py",
            "chunk_index": 0,
            "content": "def estimate_battery_health(): return battery_health",
            "language": "Python",
            "symbol_name": "estimate_battery_health",
            "symbol_type": "function",
            "start_line": 1,
            "end_line": 2,
            "embedding": [0.1, 0.2, 0.3],
        },
        {
            "file_path": "temperature.py",
            "chunk_index": 0,
            "content": "def monitor_temperature(): return temperature",
            "language": "Python",
            "symbol_name": "monitor_temperature",
            "symbol_type": "function",
            "start_line": 1,
            "end_line": 2,
            "embedding": [0.2, 0.3, 0.4],
        },
        {
            "file_path": "capacity.py",
            "chunk_index": 0,
            "content": "def calculate_battery_capacity(): return capacity",
            "language": "Python",
            "symbol_name": "calculate_battery_capacity",
            "symbol_type": "function",
            "start_line": 1,
            "end_line": 2,
            "embedding": [0.3, 0.4, 0.5],
        },
    ]

    try:
        indexed_count = vector_store.add_chunks(
            repository_id,
            chunks,
        )

        assert indexed_count == 3

        bm25_retriever = BM25Retriever(vector_store)

        hybrid_retriever = HybridRetriever(
            vector_store=vector_store,
            embedding_service=FakeEmbeddingService(),
            bm25_retriever=bm25_retriever,
        )

        results = hybrid_retriever.retrieve(
            repository_id=repository_id,
            query="battery health",
            top_k=3,
        )

        assert len(results) > 0

        result_ids = [result["id"] for result in results]

        assert len(result_ids) == len(set(result_ids))
        assert "battery.py:0" in result_ids

        for result in results:
            assert result["content"]
            assert isinstance(result["metadata"], dict)
            assert result["rrf_score"] > 0
            assert result["rank"] > 0

    finally:
        vector_store.delete_repository(repository_id)


def test_hybrid_retrieval_with_real_cross_encoder(tmp_path):
    vector_store = VectorStore(
        persist_directory=str(tmp_path / "chroma_reranker")
    )

    repository_id = "hybrid-reranker-integration"

    chunks = [
        {
            "file_path": "battery.py",
            "chunk_index": 0,
            "content": "def estimate_battery_soh(cycles): return health_score",
            "language": "Python",
            "symbol_name": "estimate_battery_soh",
            "symbol_type": "function",
            "start_line": 1,
            "end_line": 2,
            "embedding": [0.1, 0.2, 0.3],
        },
        {
            "file_path": "routing.py",
            "chunk_index": 0,
            "content": "def calculate_route_distance(points): return distance",
            "language": "Python",
            "symbol_name": "calculate_route_distance",
            "symbol_type": "function",
            "start_line": 1,
            "end_line": 2,
            "embedding": [0.2, 0.3, 0.4],
        },
        {
            "file_path": "degradation.py",
            "chunk_index": 0,
            "content": "def predict_battery_degradation(history): return degradation_rate",
            "language": "Python",
            "symbol_name": "predict_battery_degradation",
            "symbol_type": "function",
            "start_line": 1,
            "end_line": 2,
            "embedding": [0.3, 0.4, 0.5],
        },
    ]

    try:
        assert vector_store.add_chunks(repository_id, chunks) == 3

        bm25_retriever = BM25Retriever(vector_store)
        reranker = CrossEncoderReranker()

        hybrid_retriever = HybridRetriever(
            vector_store=vector_store,
            embedding_service=FakeEmbeddingService(),
            bm25_retriever=bm25_retriever,
            reranker=reranker,
        )

        results = hybrid_retriever.retrieve(
            repository_id=repository_id,
            query="battery state of health estimation and degradation",
            top_k=3,
        )

        assert len(results) == 3

        scores = [result["rerank_score"] for result in results]

        assert scores == sorted(scores, reverse=True)
        assert [result["rank"] for result in results] == [1, 2, 3]

        assert results[-1]["id"] == "routing.py:0"

    finally:
        vector_store.delete_repository(repository_id)
