
from functools import lru_cache
from typing import Any

from sentence_transformers import SentenceTransformer


DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_BATCH_SIZE = 32


class EmbeddingService:
    """Generate normalized semantic embeddings for repository code chunks."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero.")

        self.model_name = model_name
        self.batch_size = batch_size
        self._model = None

    def _load_model(self) -> SentenceTransformer:
        """Load the embedding model lazily and reuse it."""
        if self._model is None:
            self._model = SentenceTransformer(
                self.model_name,
                device="cpu",
            )

        return self._model

    def generate_embeddings(
        self,
        chunks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Generate one embedding per code chunk.

        Returns the original chunk metadata with an additional
        'embedding' field containing the embedding vector.
        """
        if not chunks:
            return []

        contents = []

        for index, chunk in enumerate(chunks):
            if not isinstance(chunk, dict):
                raise TypeError(
                    f"Chunk at index {index} must be a dictionary."
                )

            content = chunk.get("content")

            if not isinstance(content, str) or not content.strip():
                raise ValueError(
                    f"Chunk at index {index} has missing or empty content."
                )

            contents.append(content)

        model = self._load_model()

        embeddings = model.encode(
            contents,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        if len(embeddings) != len(chunks):
            raise RuntimeError(
                "The number of generated embeddings does not "
                "match the number of input chunks."
            )

        results = []

        for chunk, embedding in zip(chunks, embeddings):
            results.append({
                **chunk,
                "embedding": embedding.tolist(),
            })

        return results


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Return a shared embedding service instance."""
    return EmbeddingService()
