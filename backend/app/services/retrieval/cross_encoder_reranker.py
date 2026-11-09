import math
from typing import Any

from sentence_transformers import CrossEncoder


DEFAULT_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class CrossEncoderReranker:
    """Rerank retrieved repository chunks using a Cross-Encoder."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        model: Any = None,
    ) -> None:
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("model_name must be a non-empty string.")

        self.model_name = model_name
        self._model = model

    def _get_model(self):
        """Load the model lazily and reuse it."""

        if self._model is None:
            self._model = CrossEncoder(
                self.model_name,
                device="cpu",
            )

        return self._model

    def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Score query-document pairs and return the highest-ranked chunks."""

        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string.")

        if not isinstance(documents, list):
            raise ValueError("documents must be a list.")

        if (
            not isinstance(top_k, int)
            or isinstance(top_k, bool)
            or top_k <= 0
        ):
            raise ValueError("top_k must be a positive integer.")

        if not documents:
            return []

        pairs = []

        for index, document in enumerate(documents):
            if not isinstance(document, dict):
                raise ValueError(
                    f"Document at index {index} must be a dictionary."
                )

            content = document.get("content")

            if not isinstance(content, str) or not content.strip():
                raise ValueError(
                    f"Document at index {index} has missing or empty content."
                )

            pairs.append((query, content))

        model = self._get_model()

        scores = model.predict(pairs)

        if len(scores) != len(documents):
            raise ValueError(
                "Cross-Encoder returned an unexpected number of scores."
            )

        ranked_documents = []

        for document, score in zip(documents, scores):
            score = float(score)

            if not math.isfinite(score):
                raise ValueError(
                    "Cross-Encoder returned a non-finite score."
                )

            result = document.copy()
            result["rerank_score"] = score
            ranked_documents.append(result)

        ranked_documents.sort(
            key=lambda item: item["rerank_score"],
            reverse=True,
        )

        for rank, document in enumerate(
            ranked_documents[:top_k],
            start=1,
        ):
            document["rank"] = rank

        return ranked_documents[:top_k]
