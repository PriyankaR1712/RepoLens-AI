
from pathlib import Path

from app.services.analysis.python_parser import parse_python_file


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
