
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
    """Create a standardized code chunk with source-location metadata."""
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
    Oversized classes are split into class-context and method chunks.
    Small standalone functions are kept intact.
    Oversized functions are split at line boundaries.
    Files without extracted symbols are preserved when source is supplied.
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
            return _split_content(
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

        return []

    # Select top-level classes and functions.
    top_level_symbols = [
        symbol
        for symbol in symbols
        if symbol.get("type") in {"class", "function"}
        and symbol.get("parent_class") is None
        and symbol.get("parent_function") is None
    ]

    # Process symbols in original source order.
    top_level_symbols.sort(
        key=lambda symbol: (
            symbol.get("start_line", 0),
            symbol.get("end_line", 0),
        )
    )

    for symbol in top_level_symbols:
        if (
            symbol.get("type") == "class"
            and len(symbol.get("source", "")) > max_chunk_size
        ):
            symbol_chunks = _chunk_oversized_class(
                class_symbol=symbol,
                symbols=symbols,
                file_path=file_path,
                language=language,
                chunk_index=chunk_index,
                max_chunk_size=max_chunk_size,
            )
        else:
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


def _chunk_oversized_class(
    class_symbol: dict[str, Any],
    symbols: list[dict[str, Any]],
    file_path: str,
    language: str,
    chunk_index: int,
    max_chunk_size: int,
) -> list[dict[str, Any]]:
    """
    Split an oversized class into class-context and method chunks.

    Class declarations and class-level attributes are preserved.
    Methods are extracted separately with their original locations
    and parent-class metadata.
    """
    class_name = class_symbol["name"]
    class_start = class_symbol["start_line"]
    class_end = class_symbol["end_line"]

    methods = [
        symbol
        for symbol in symbols
        if symbol.get("type") == "method"
        and symbol.get("parent_class") == class_name
        and class_start <= symbol.get("start_line", 0)
        and symbol.get("end_line", 0) <= class_end
    ]

    methods.sort(key=lambda symbol: symbol["start_line"])

    # If no methods are available, fall back to normal splitting.
    if not methods:
        return _split_content(
            content=class_symbol["source"],
            file_path=file_path,
            language=language,
            symbol_name=class_name,
            symbol_type="class",
            parent_class=None,
            start_line=class_start,
            chunk_index=chunk_index,
            max_chunk_size=max_chunk_size,
        )

    # Identify the original lines occupied by methods.
    method_lines = set()

    for method in methods:
        method_lines.update(
            range(
                method["start_line"],
                method["end_line"] + 1,
            )
        )

    class_lines = class_symbol["source"].splitlines(keepends=True)

    # Preserve class declaration and class-level attributes.
    context_segments = []
    current_segment = []
    current_start_line = None

    for offset, line in enumerate(class_lines):
        original_line = class_start + offset

        if original_line in method_lines:
            if current_segment:
                context_segments.append(
                    (current_start_line, "".join(current_segment))
                )
                current_segment = []
                current_start_line = None

            continue

        if current_start_line is None:
            current_start_line = original_line

        current_segment.append(line)

    if current_segment:
        context_segments.append(
            (current_start_line, "".join(current_segment))
        )

    chunks = []

    # Create class-context chunks.
    for segment_start, segment_content in context_segments:
        if not segment_content.strip():
            continue

        segment_chunks = _split_content(
            content=segment_content,
            file_path=file_path,
            language=language,
            symbol_name=class_name,
            symbol_type="class_context",
            parent_class=None,
            start_line=segment_start,
            chunk_index=chunk_index + len(chunks),
            max_chunk_size=max_chunk_size,
        )

        chunks.extend(segment_chunks)

    # Create individual method chunks.
    for method in methods:
        method_chunks = _split_content(
            content=method["source"],
            file_path=file_path,
            language=language,
            symbol_name=method["name"],
            symbol_type="method",
            parent_class=class_name,
            start_line=method["start_line"],
            chunk_index=chunk_index + len(chunks),
            max_chunk_size=max_chunk_size,
        )

        chunks.extend(method_chunks)

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
    Split oversized source content at line boundaries.

    Original source line numbers and chunk metadata are preserved.
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
                end_line=start_line + max(
                    0, len(content.splitlines()) - 1
                ),
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
                    + len(current_lines) - 1,
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
                end_line=current_start_line + len(current_lines) - 1,
                chunk_index=chunk_index + len(chunks),
                parent_class=parent_class,
            )
        )

    return chunks
