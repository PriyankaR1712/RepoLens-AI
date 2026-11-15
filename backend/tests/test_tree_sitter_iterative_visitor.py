import gc
from pathlib import Path

from app.services.analysis.tree_sitter_parser import parse_tree_sitter_file


def test_nested_classes_methods_and_functions_preserve_symbol_order_and_parents():
    source = """class Outer {
  method() {
    class Inner {
      run() {
        return 1;
      }
    }
    function helper() {
      function nested() {
        return 2;
      }
    }
  }
  other() {}
}
function top() {}
"""

    result = parse_tree_sitter_file(source, "JavaScript", "nested.js")

    assert result["status"] == "success"
    assert [symbol["name"] for symbol in result["symbols"]] == [
        "Outer", "method", "Inner", "run", "helper", "nested", "other", "top"
    ]
    symbols = {symbol["name"]: symbol for symbol in result["symbols"]}
    assert symbols["Inner"]["parent_class"] == "Outer"
    assert symbols["Inner"]["parent_function"] == "method"
    assert symbols["run"]["parent_class"] == "Inner"
    assert symbols["run"]["parent_function"] == "method"
    assert symbols["helper"]["type"] == "nested_function"
    assert symbols["helper"]["parent_class"] == "Outer"
    assert symbols["helper"]["parent_function"] == "method"
    assert symbols["nested"]["parent_function"] == "helper"
    assert symbols["other"]["type"] == "method"
    assert symbols["other"]["parent_class"] == "Outer"
    assert symbols["top"]["type"] == "function"
    assert symbols["top"]["parent_class"] is None


def test_symbol_source_positions_and_syntax_error_column_are_preserved():
    valid_source = """const first = () => 1;
class Box {
  read(value) {
    return value;
  }
}
"""
    parsed = parse_tree_sitter_file(valid_source, "JavaScript", "box.js")
    assert parsed["status"] == "success"
    symbols = {symbol["name"]: symbol for symbol in parsed["symbols"]}
    assert (symbols["first"]["start_line"], symbols["first"]["end_line"]) == (1, 1)
    assert (symbols["Box"]["start_line"], symbols["Box"]["end_line"]) == (2, 6)
    assert (symbols["read"]["start_line"], symbols["read"]["end_line"]) == (3, 5)
    assert symbols["read"]["source"] == "read(value) {\n    return value;\n  }"

    invalid_source = "function broken() {\n  const value = ;\n}\n"
    invalid = parse_tree_sitter_file(invalid_source, "JavaScript", "broken.js")
    assert invalid["status"] == "partial"
    assert invalid["error"]["line"] == 2
    assert invalid["error"]["column"] == 15


def test_deeply_nested_tree_parses_without_python_recursion():
    nesting = 1100
    source = (
        "function deep() {\n"
        + "if (true) {\n" * nesting
        + "return 1;\n"
        + "}\n" * nesting
        + "}\n"
    )

    result = parse_tree_sitter_file(source, "JavaScript", "deep.js")

    assert result["status"] == "success"
    assert result["total_symbols"] == 1
    assert result["symbols"][0]["name"] == "deep"
    assert result["symbols"][0]["start_line"] == 1
    # Tree-sitter may recover with synthetic/error nodes at extreme nesting;
    # the regression target is that the visitor completes without Python
    # recursion, retaining the function's source start and name.


def test_schedulix_cpu_scheduler_regression_survives_explicit_gc():
    fixture = Path(__file__).parent / "fixtures" / "CpuScheduler.jsx"
    source = fixture.read_text(encoding="utf-8")

    result = parse_tree_sitter_file(
        source,
        "JavaScript",
        "frontend/src/components/CpuScheduler.jsx",
    )
    collected = gc.collect()

    assert result["status"] == "success"
    assert result["total_symbols"] == 33
    assert collected >= 0
