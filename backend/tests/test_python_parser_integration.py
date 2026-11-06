
from pathlib import Path

from app.services.analysis.python_parser import parse_python_file
from app.services.chunking.code_chunker import chunk_parsed_file

def test_parse_actual_ingestion_source_files():
    backend_dir = Path(__file__).resolve().parents[1]

    ingestion_dir = (
        backend_dir
        / "app"
        / "services"
        / "ingestion"
    )

    source_files = list(ingestion_dir.glob("*.py"))

    assert source_files, "No Python source files found."

    for file_path in source_files:
        source_code = file_path.read_text(encoding="utf-8")

        result = parse_python_file(
            source_code=source_code,
            file_path=str(file_path.relative_to(backend_dir)),
        )

        assert result["status"] == "success", (
            f"Failed to parse {file_path.name}: {result['error']}"
        )

        assert result["file_path"] == str(
            file_path.relative_to(backend_dir)
        )

        assert isinstance(result["symbols"], list)
def test_python_parser_output_can_be_chunked():
    source = """
class Calculator:
    def add(self, a, b):
        return a + b

def multiply(a, b):
    return a * b
"""

    parsed_result = parse_python_file(
        source_code=source,
        file_path="calculator.py",
    )

    assert parsed_result["status"] == "success"

    chunks = chunk_parsed_file(parsed_result)

    assert len(chunks) > 0

    actual_names = {
        chunk["symbol_name"] for chunk in chunks
    }

    assert "Calculator" in actual_names
    assert "multiply" in actual_names

    for chunk in chunks:
        assert chunk["file_path"] == "calculator.py"
        assert chunk["language"] == "Python"
        assert chunk["content"].strip()
        assert chunk["start_line"] >= 1
        assert chunk["end_line"] >= chunk["start_line"]