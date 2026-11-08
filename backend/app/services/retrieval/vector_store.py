
from pathlib import Path
from typing import Any
import hashlib
import chromadb


DEFAULT_PERSIST_DIRECTORY = "data/chroma"


class VectorStore:
    """Manage persistent ChromaDB storage for repository code chunks."""

    def __init__(
        self,
        persist_directory: str = DEFAULT_PERSIST_DIRECTORY,
    ):
        self.persist_directory = str(Path(persist_directory))

        Path(self.persist_directory).mkdir(
            parents=True,
            exist_ok=True,
        )

        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
        )

    @staticmethod
    def _validate_collection_name(repository_id: str) -> str:
        """Generate a stable, valid collection name for a repository."""
        if not isinstance(repository_id, str) or not repository_id.strip():
            raise ValueError("repository_id must be a non-empty string.")

        normalized_id = repository_id.strip().lower()

        repository_hash = hashlib.sha256(
            normalized_id.encode("utf-8")
        ).hexdigest()[:16]

        return f"repo_{repository_hash}"

    def get_or_create_collection(self, repository_id: str):
        """Get an existing repository collection or create it."""
        collection_name = self._validate_collection_name(repository_id)

        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={"repository_id": repository_id},
            embedding_function=None,
        )

    @staticmethod
    def _prepare_metadata(chunk: dict[str, Any]) -> dict[str, Any]:
        """Convert chunk metadata into ChromaDB-compatible values."""
        metadata = {
            "file_path": chunk["file_path"],
            "language": chunk["language"],
            "symbol_name": chunk["symbol_name"],
            "symbol_type": chunk["symbol_type"],
            "parent_class": chunk.get("parent_class") or "",
            "start_line": int(chunk["start_line"]),
            "end_line": int(chunk["end_line"]),
            "chunk_index": int(chunk["chunk_index"]),
        }

        required_string_fields = [
            "file_path",
            "language",
            "symbol_name",
            "symbol_type",
        ]

        for key in required_string_fields:
            if not metadata[key].strip():
                raise ValueError(
                    f"Chunk metadata field '{key}' cannot be empty."
                )

        return metadata

    def add_chunks(
        self,
        repository_id: str,
        chunks: list[dict[str, Any]],
    ) -> int:
        """Store embedded code chunks in a repository collection."""
        if not chunks:
            return 0

        collection = self.get_or_create_collection(repository_id)

        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for index, chunk in enumerate(chunks):
            if not isinstance(chunk, dict):
                raise TypeError(f"Chunk at index {index} must be a dictionary.")

            content = chunk.get("content")
            embedding = chunk.get("embedding")

            if not isinstance(content, str) or not content.strip():
                raise ValueError(f"Chunk at index {index} has empty content.")

            if not isinstance(embedding, list) or not embedding:
                raise ValueError(f"Chunk at index {index} has no valid embedding.")

            if not all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                for value in embedding
            ):
                raise ValueError(f"Chunk at index {index} has invalid embedding values.")

            metadata = self._prepare_metadata(chunk)

            chunk_id = (
                f"{metadata['file_path']}:"
                f"{metadata['chunk_index']}"
            )

            ids.append(chunk_id)
            documents.append(content)
            embeddings.append(embedding)
            metadatas.append(metadata)

        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        return len(ids)

    def search(
        self,
        repository_id: str,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Find the most semantically similar code chunks."""
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")

        if not query_embedding or not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            for value in query_embedding
        ):
            raise ValueError("query_embedding must contain numeric values.")

        collection = self.get_or_create_collection(repository_id)

        if collection.count() == 0:
            return []

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        matches = []

        for index, chunk_id in enumerate(results["ids"][0]):
            matches.append({
                "id": chunk_id,
                "content": results["documents"][0][index],
                "metadata": results["metadatas"][0][index],
                "distance": results["distances"][0][index],
            })

        return matches

    def delete_repository(self, repository_id: str) -> bool:
        """Delete all indexed vectors belonging to a repository."""
        collection_name = self._validate_collection_name(repository_id)

        try:
            self.client.delete_collection(name=collection_name)
            return True
        except Exception as exc:
            if "does not exist" in str(exc).lower():
                return False
            raise
