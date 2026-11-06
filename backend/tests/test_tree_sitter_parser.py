
from app.services.analysis.tree_sitter_parser import (
    parse_tree_sitter_file,
)
from app.services.chunking.code_chunker import chunk_parsed_file

def test_parse_javascript_function():
    source = """function greet(name) {
    return `Hello ${name}`;
}
"""

    result = parse_tree_sitter_file(
        source, "JavaScript", "greetings.js"
    )

    assert result["status"] == "success"
    assert result["total_symbols"] == 1

    function = result["symbols"][0]

    assert function["name"] == "greet"
    assert function["type"] == "function"
    assert function["arguments"] == ["name"]
    assert function["start_line"] == 1
    assert function["end_line"] == 3


def test_parse_javascript_class_and_methods():
    source = """class Student {
    constructor(name) {
        this.name = name;
    }

    greet() {
        return this.name;
    }
}
"""

    result = parse_tree_sitter_file(source, "JavaScript")

    assert result["status"] == "success"
    assert result["total_symbols"] == 3

    student, constructor, greet = result["symbols"]

    assert student["name"] == "Student"
    assert student["type"] == "class"

    assert constructor["name"] == "constructor"
    assert constructor["type"] == "method"
    assert constructor["parent_class"] == "Student"
    assert constructor["arguments"] == ["name"]

    assert greet["name"] == "greet"
    assert greet["type"] == "method"
    assert greet["parent_class"] == "Student"


def test_parse_javascript_arrow_function():
    source = """const add = (a, b) => {
    return a + b;
};
"""

    result = parse_tree_sitter_file(source, "JavaScript")

    assert result["status"] == "success"
    assert result["total_symbols"] == 1

    function = result["symbols"][0]

    assert function["name"] == "add"
    assert function["type"] == "function"
    assert function["arguments"] == ["a", "b"]


def test_parse_typescript_function():
    source = """function calculate(a: number, b: number): number {
    return a + b;
}
"""

    result = parse_tree_sitter_file(source, "TypeScript")

    assert result["status"] == "success"
    assert result["total_symbols"] == 1

    function = result["symbols"][0]

    assert function["name"] == "calculate"
    assert function["type"] == "function"
    assert function["arguments"] == ["a", "b"]


def test_parse_typescript_interface():
    source = """interface User {
    name: string;
    age: number;
}
"""

    result = parse_tree_sitter_file(source, "TypeScript")

    assert result["status"] == "success"
    assert result["total_symbols"] == 1

    interface = result["symbols"][0]

    assert interface["name"] == "User"
    assert interface["type"] == "class"


def test_parse_tsx_component():
    source = """function Welcome({ name }) {
    return <h1>Hello, {name}!</h1>;
}
"""

    result = parse_tree_sitter_file(source, "TSX")

    assert result["status"] == "success"
    assert result["total_symbols"] == 1

    component = result["symbols"][0]

    assert component["name"] == "Welcome"
    assert component["type"] == "function"


def test_parse_java_class_and_method():
    source = """public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
}
"""

    result = parse_tree_sitter_file(source, "Java")

    assert result["status"] == "success"
    assert result["total_symbols"] == 2

    calculator, add = result["symbols"]

    assert calculator["name"] == "Calculator"
    assert calculator["type"] == "class"

    assert add["name"] == "add"
    assert add["type"] == "method"
    assert add["parent_class"] == "Calculator"
    assert add["arguments"] == ["int a", "int b"]


def test_unsupported_language():
    result = parse_tree_sitter_file(
        "print('hello')", "Ruby"
    )

    assert result["status"] == "failed"
    assert result["total_symbols"] == 0
    assert result["symbols"] == []
    assert result["error"] is not None
