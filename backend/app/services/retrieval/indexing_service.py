

from pathlib import Path

from app.services.analysis.python_parser import parse_python_file
from app.services.analysis.tree_sitter_parser import parse_tree_sitter_file
from app.services.chunking.code_chunker import chunk_parsed_file
from app.services.embeddings.embedding_service import get_embedding_service
from app.services.retrieval.vector_store import VectorStore


TREE_SITTER_LANGUAGES = {
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TSX",
    ".java": "Java",
}


def parse_source_file(source_code: str, file_path: str) -> dict:
    """Select the appropriate parser based on the file extension."""

    extension = Path(file_path).suffix.lower()

    if extension == ".py":
        return parse_python_file(source_code, file_path)

    language = TREE_SITTER_LANGUAGES.get(extension)

    if language:
        return parse_tree_sitter_file(
            source_code=source_code,
            language=language,
            file_path=file_path,
        )

    return {
        "status": "failed",
        "language": "Unknown",
        "file_path": file_path,
        "total_symbols": 0,
        "symbols": [],
        "error": {
            "message": f"Unsupported file extension: {extension}",
            "line": None,
            "column": None,
        },
    }


class IndexingService:
    """Coordinate parsing, chunking, embedding, and vector storage."""

    def __init__(
        self,
        vector_store=None,
        embedding_service=None,
    ):
        self.vector_store = vector_store or VectorStore()
        self.embedding_service = (
            embedding_service or get_embedding_service()
        )

    def index_repository(
        self,
        ingestion_result: dict,
        repository_id: str,
    ) -> dict:
        """Index successfully ingested source files for a repository."""

        if not isinstance(ingestion_result, dict):
            raise ValueError("ingestion_result must be a dictionary.")

        if not isinstance(repository_id, str) or not repository_id.strip():
            raise ValueError("repository_id must be a non-empty string.")

        if ingestion_result.get("status") not in {"success", "partial"}:
            raise ValueError("Repository ingestion was not successful.")

        files = ingestion_result.get("files", [])

        if not isinstance(files, list):
            raise ValueError("ingestion_result['files'] must be a list.")

        result = {
            "status": (
                "partial"
                if ingestion_result["status"] == "partial"
                else "success"
            ),
            "repository_id": repository_id,
            "total_files": len(files),
            "processed_files": 0,
            "failed_files": 0,
            "total_symbols": 0,
            "total_chunks": 0,
            "indexed_chunks": 0,
            "errors": [],
        }

        all_chunks = []

        for index, file in enumerate(files):
            if not isinstance(file, dict):
                result["failed_files"] += 1
                result["status"] = "partial"
                result["errors"].append({
                    "file_path": f"<file at index {index}>",
                    "message": "File entry must be a dictionary.",
                })
                continue

            file_path = file.get("path", "<unknown>")
            source_code = file.get("content")

            if not isinstance(file_path, str) or not file_path.strip():
                result["failed_files"] += 1
                result["status"] = "partial"
                result["errors"].append({
                    "file_path": "<unknown>",
                    "message": "File path is missing or invalid.",
                })
                continue

            if not isinstance(source_code, str):
                result["failed_files"] += 1
                result["status"] = "partial"
                result["errors"].append({
                    "file_path": file_path,
                    "message": "File content is missing or invalid.",
                })
                continue

            try:
                parsed_result = parse_source_file(
                    source_code,
                    file_path,
                )

                if (
                    not isinstance(parsed_result, dict)
                    or parsed_result.get("status")
                    not in {"success", "partial", "failed"}
                ):
                    raise ValueError("Parser returned an invalid result.")

                if parsed_result["status"] == "failed":
                    result["failed_files"] += 1
                    result["status"] = "partial"
                    result["errors"].append({
                        "file_path": file_path,
                        "message": (
                            (parsed_result.get("error") or {}).get(
                                "message", "Parsing failed."
                            )
                        ),
                    })
                    continue

                parsed_result_for_chunking = {
                    **parsed_result,
                    "source": source_code,
                }

                chunks = chunk_parsed_file(
                    parsed_result_for_chunking
                )

                if not isinstance(chunks, list):
                    raise ValueError("Chunker returned an invalid result.")

                result["processed_files"] += 1
                result["total_symbols"] += parsed_result.get(
                    "total_symbols", 0
                )

                all_chunks.extend(chunks)

                if parsed_result["status"] == "partial":
                    result["status"] = "partial"
                    result["errors"].append({
                        "file_path": file_path,
                        "message": (
                            (parsed_result.get("error") or {}).get(
                                "message", "Partial parsing warning."
                            )
                        ),
                    })

            except Exception as exc:
                result["failed_files"] += 1
                result["status"] = "partial"
                result["errors"].append({
                    "file_path": file_path,
                    "message": str(exc),
                })


        result["total_chunks"] = len(all_chunks)

        # Only a completely successful run may remove obsolete chunks.
        can_synchronize = (
            result["status"] == "success"
            and result["failed_files"] == 0
            and not result["errors"]
        )

        # A complete empty repository must also remove its old index.
        if not all_chunks:
            if can_synchronize:
                try:
                    self.vector_store.sync_chunks(repository_id, [])
                except Exception as exc:
                    result["status"] = "failed"
                    result["errors"].append({
                        "stage": "storage",
                        "message": str(exc),
                    })
            return result

        try:
            embedded_chunks = (
                self.embedding_service.generate_embeddings(all_chunks)
            )
        except Exception as exc:
            result["status"] = "failed"
            result["errors"].append({
                "stage": "embedding",
                "message": str(exc),
            })
            return result

        if (
            not isinstance(embedded_chunks, list)
            or len(embedded_chunks) != len(all_chunks)
        ):
            result["status"] = "failed"
            result["errors"].append({
                "stage": "embedding",
                "message": (
                    "Embedding service returned an invalid number "
                    "of embedded chunks."
                ),
            })
            return result

        try:
            if can_synchronize:
                indexed_count = self.vector_store.sync_chunks(
                    repository_id,
                    embedded_chunks,
                )
            else:
                indexed_count = self.vector_store.add_chunks(
                    repository_id,
                    embedded_chunks,
                )

        except Exception as exc:
            result["status"] = "failed"
            result["errors"].append({
                "stage": "storage",
                "message": str(exc),
            })
            return result

        if (
            not isinstance(indexed_count, int)
            or isinstance(indexed_count, bool)
            or indexed_count != len(all_chunks)
        ):
            result["status"] = "failed"
            result["errors"].append({
                "stage": "storage",
                "message": (
                    "The number of indexed chunks does not match "
                    "the number of generated chunks."
                ),
            })
            return result

        result["indexed_chunks"] = indexed_count

        return result
