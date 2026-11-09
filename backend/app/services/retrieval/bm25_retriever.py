
import math
import re
from collections import Counter
from typing import Any


def tokenize_code(text: str) -> list[str]:
    """Tokenize code and natural language while preserving useful identifiers."""

    if not isinstance(text, str):
        return []

    # Split camelCase and PascalCase identifiers.
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)

    # Split acronym boundaries, e.g. HTTPResponse -> HTTP Response.
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)

    # Split snake_case and punctuation-separated identifiers.
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())

    return tokens


class BM25Retriever:
    """Retrieve repository code chunks using BM25 keyword relevance."""

    def __init__(
        self,
        vector_store: Any,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        if k1 <= 0:
            raise ValueError("k1 must be greater than zero.")

        if not 0 <= b <= 1:
            raise ValueError("b must be between 0 and 1.")

        self.vector_store = vector_store
        self.k1 = k1
        self.b = b

    def retrieve(
        self,
        repository_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Return the most relevant repository chunks for a keyword query."""

        if not isinstance(repository_id, str) or not repository_id.strip():
            raise ValueError("repository_id must be a non-empty string.")

        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string.")

        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
            raise ValueError("top_k must be a positive integer.")

        query_tokens = tokenize_code(query)

        if not query_tokens:
            return []

        collection = self.vector_store.get_or_create_collection(repository_id)

        stored_chunks = collection.get(
            include=["documents", "metadatas"]
        )

        chunk_ids = stored_chunks.get("ids") or []
        documents = stored_chunks.get("documents") or []
        metadatas = stored_chunks.get("metadatas") or []

        if not documents:
            return []

        corpus = []
        results = []

        for index, document in enumerate(documents):
            if not isinstance(document, str) or not document.strip():
                continue

            tokens = tokenize_code(document)

            if not tokens:
                continue

            corpus.append(tokens)

            metadata = (
                metadatas[index]
                if index < len(metadatas) and metadatas[index] is not None
                else {}
            )

            chunk_id = (
                chunk_ids[index]
                if index < len(chunk_ids)
                else None
            )

            results.append({
                "id": chunk_id,
                "content": document,
                "metadata": metadata,
            })

        if not corpus:
            return []

        document_count = len(corpus)
        document_lengths = [len(tokens) for tokens in corpus]
        average_length = sum(document_lengths) / document_count

        document_frequencies = Counter()

        for tokens in corpus:
            document_frequencies.update(set(tokens))

        scores = []

        for index, tokens in enumerate(corpus):
            term_frequencies = Counter(tokens)
            document_length = document_lengths[index]
            score = 0.0

            for term in query_tokens:
                frequency = term_frequencies.get(term, 0)

                if frequency == 0:
                    continue

                df = document_frequencies[term]

                inverse_document_frequency = math.log(
                    1 + (
                        document_count - df + 0.5
                    ) / (df + 0.5)
                )

                length_normalization = self.k1 * (
                    1 - self.b
                    + self.b * document_length / average_length
                )

                term_score = (
                    inverse_document_frequency
                    * frequency * (self.k1 + 1)
                    / (frequency + length_normalization)
                )

                score += term_score

            if score > 0:
                scores.append((score, index))

        scores.sort(key=lambda item: item[0], reverse=True)

        ranked_results = []

        for score, index in scores[:top_k]:
            result = results[index].copy()
            result["score"] = score
            ranked_results.append(result)

        return ranked_results

        for score, index in scores[:top_k]:
            result = results[index].copy()
            result["score"] = score
            results_for_return = result

            # Preserve the original chunk content and metadata.
            if results_for_return["id"] is not None:
                pass

            # Append the scored result.
            if "ranked_results" not in locals():
                ranked_results = []

            ranked_results.append(results_for_return)

        return ranked_results if "ranked_results" in locals() else []
