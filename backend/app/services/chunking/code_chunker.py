
from typing import Any


# Maximum target size for a code chunk, measured in characters.
DEFAULT_MAX_CHUNK_SIZE = 3000


def create_code_chunk(
    file_path: str,
    language: str,
    symbol_name: str,
    symbol_type: str,
    content: str,
    start_line: int,
    end_line: int,
    chunk_index: int,
    parent_class: str | None = None,
) -> dict[str, Any]:
    """
    Create a standardized code chunk with source-location metadata.
    """
    return {
        "file_path": file_path,
        "language": language,
        "symbol_name": symbol_name,
        "symbol_type": symbol_type,
        "parent_class": parent_class,
        "start_line": start_line,
        "end_line": end_line,
        "content": content,
        "chunk_index": chunk_index,
    }


def chunk_parsed_file(
    parsed_result: dict[str, Any],
    max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
) -> list[dict[str, Any]]:
    """
    Convert parser output into non-overlapping, metadata-rich code chunks.

    Small classes are kept intact.
    Small standalone functions are kept intact.
    Methods are not duplicated when their parent class is included.
    Oversized symbols are split by source lines.
    Files without extracted symbols are preserved as file-level chunks.
    """
    if max_chunk_size <= 0:
        raise ValueError("max_chunk_size must be greater than zero.")

    if parsed_result.get("status") not in {"success", "partial"}:
        return []

    file_path = parsed_result.get("file_path", "")
    language = parsed_result.get("language", "Unknown")
    symbols = parsed_result.get("symbols", [])

    chunks = []
    chunk_index = 0

    if not symbols:
        source = parsed_result.get("source", "")

        if source.strip():
            chunks.extend(
                _split_content(
                    content=source,
                    file_path=file_path,
                    language=language,
                    symbol_name=file_path or "file",
                    symbol_type="file",
                    parent_class=None,
                    start_line=1,
                    chunk_index=chunk_index,
                    max_chunk_size=max_chunk_size,
                )
            )

        return chunks

    # Keep only top-level symbols.
    # Methods and nested functions are already represented
    # inside their parent class/function source.
    top_level_symbols = [
        symbol
        for symbol in symbols
        if symbol.get("type") in {"class", "function"}
        and symbol.get("parent_class") is None
        and symbol.get("parent_function") is None
    ]

    # Sort symbols by their original source location.
    top_level_symbols.sort(
        key=lambda symbol: (
            symbol.get("start_line", 0),
            symbol.get("end_line", 0),
        )
    )

    for symbol in top_level_symbols:
        symbol_chunks = _split_content(
            content=symbol.get("source", ""),
            file_path=file_path,
            language=language,
            symbol_name=symbol.get("name", "unknown"),
            symbol_type=symbol.get("type", "unknown"),
            parent_class=None,
            start_line=symbol.get("start_line", 1),
            chunk_index=chunk_index,
            max_chunk_size=max_chunk_size,
        )

        chunks.extend(symbol_chunks)
        chunk_index += len(symbol_chunks)

    return chunks


def _split_content(
    content: str,
    file_path: str,
    language: str,
    symbol_name: str,
    symbol_type: str,
    parent_class: str | None,
    start_line: int,
    chunk_index: int,
    max_chunk_size: int,
) -> list[dict[str, Any]]:
    """
    Split oversized source content into line-preserving chunks.

    This initial implementation splits at line boundaries.
    Later, we can improve oversized function splitting using
    syntax-aware boundaries.
    """
    if not content.strip():
        return []

    if len(content) <= max_chunk_size:
        return [
            create_code_chunk(
                file_path=file_path,
                language=language,
                symbol_name=symbol_name,
                symbol_type=symbol_type,
                content=content,
                start_line=start_line,
                end_line=start_line + max(0, len(content.splitlines()) - 1),
                chunk_index=chunk_index,
                parent_class=parent_class,
            )
        ]

    lines = content.splitlines(keepends=True)

    chunks = []
    current_lines = []
    current_size = 0
    current_start_line = start_line

    for line_number, line in enumerate(lines):
        if current_lines and current_size + len(line) > max_chunk_size:
            chunk_content = "".join(current_lines)

            chunks.append(
                create_code_chunk(
                    file_path=file_path,
                    language=language,
                    symbol_name=symbol_name,
                    symbol_type=symbol_type,
                    content=chunk_content,
                    start_line=current_start_line,
                    end_line=current_start_line
                    + chunk_content.count("\n")
                    - (1 if chunk_content.endswith("\n") else 0),
                    chunk_index=chunk_index + len(chunks),
                    parent_class=parent_class,
                )
            )

            current_lines = []
            current_size = 0
            current_start_line = start_line + line_number

        current_lines.append(line)
        current_size += len(line)

    if current_lines:
        chunk_content = "".join(current_lines)

        chunks.append(
            create_code_chunk(
                file_path=file_path,
                language=language,
                symbol_name=symbol_name,
                symbol_type=symbol_type,
                content=chunk_content,
                start_line=current_start_line,
                end_line=current_start_line
                + chunk_content.count("\n")
                - (1 if chunk_content.endswith("\n") else 0),
                chunk_index=chunk_index + len(chunks),
                parent_class=parent_class,
            )
        )

    return chunks
