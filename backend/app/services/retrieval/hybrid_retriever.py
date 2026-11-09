
from typing import Any
from unittest import result

from app.services.retrieval.bm25_retriever import BM25Retriever


class HybridRetriever:
    """Combine semantic and keyword retrieval using Reciprocal Rank Fusion."""

    def __init__(
        self,
        vector_store: Any,
        embedding_service: Any,
        bm25_retriever: BM25Retriever | None = None,
        rrf_k: int = 60,
        reranker: Any = None,
    ) -> None:
        if not isinstance(rrf_k, int) or isinstance(rrf_k, bool) or rrf_k <= 0:
            raise ValueError("rrf_k must be a positive integer.")

        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.bm25_retriever = bm25_retriever or BM25Retriever(vector_store)
        self.rrf_k = rrf_k
        self.reranker = reranker

    def retrieve(
        self,
        repository_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve and fuse semantic and keyword search results."""

        if not isinstance(repository_id, str) or not repository_id.strip():
            raise ValueError("repository_id must be a non-empty string.")

        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string.")

        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
            raise ValueError("top_k must be a positive integer.")

        candidate_k = max(top_k * 3, top_k)

        # Generate an embedding for the user's query.
        query_embedding_result = self.embedding_service.generate_embeddings(
            [{"content": query}]
        )

        if (
            not isinstance(query_embedding_result, list)
            or len(query_embedding_result) != 1
            or not isinstance(query_embedding_result[0], dict)
        ):
            raise ValueError("Query embedding generation returned an invalid result.")

        query_embedding = query_embedding_result[0].get("embedding")

        if not isinstance(query_embedding, list) or not query_embedding:
            raise ValueError("Query embedding is missing or invalid.")

        # Retrieve candidates from both retrieval methods.
        semantic_results = self.vector_store.search(
            repository_id=repository_id,
            query_embedding=query_embedding,
            top_k=candidate_k,
        )

        keyword_results = self.bm25_retriever.retrieve(
            repository_id=repository_id,
            query=query,
            top_k=candidate_k,
        )

        # Reciprocal Rank Fusion.
        fused_results = {}

        for results in (semantic_results, keyword_results):
            if not isinstance(results, list):
                raise ValueError("Retriever returned an invalid result list.")

            seen_in_ranking = set()

            for rank, result in enumerate(results, start=1):
                if not isinstance(result, dict):
                    continue

                chunk_id = result.get("id")

                if not isinstance(chunk_id, str) or not chunk_id:
                    continue

                if chunk_id in seen_in_ranking:
                    continue

                seen_in_ranking.add(chunk_id)

                if chunk_id not in fused_results:
                    fused_results[chunk_id] = {
                        "id": chunk_id,
                        "content": result.get("content"),
                        "metadata": result.get("metadata") or {},
                        "semantic_distance": None,
                        "bm25_score": None,
                        "rrf_score": 0.0,
                    }

                fused = fused_results[chunk_id]

                # Preserve scores from their respective retrievers.
                if "distance" in result:
                    fused["semantic_distance"] = result["distance"]

                if "score" in result:
                    fused["bm25_score"] = result["score"]

                # A result receives a contribution from each ranking.
                fused["rrf_score"] += 1.0 / (self.rrf_k + rank)

        ranked_results = sorted(
            fused_results.values(),
            key=lambda item: item["rrf_score"],
            reverse=True,
        )
        if not ranked_results:
            return []

        if self.reranker is not None:
            return self.reranker.rerank(
                query=query,
                documents=ranked_results,
                top_k=top_k,
            )

        for rank, result in enumerate(ranked_results, start=1):
          result["rank"] = rank

        return ranked_results[:top_k]

        for rank, result in enumerate(ranked_results, start=1):
            result["rank"] = rank

        return ranked_results[:top_k]
