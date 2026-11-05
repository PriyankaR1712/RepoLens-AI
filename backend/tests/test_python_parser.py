
from app.services.analysis.python_parser import parse_python_file


def test_parse_simple_function():
    source = """
def greet(name):
    return f"Hello {name}"
"""

    result = parse_python_file(source, "greetings.py")

    assert result["status"] == "success"
    assert result["total_symbols"] == 1

    function = result["symbols"][0]

    assert function["name"] == "greet"
    assert function["type"] == "function"
    assert function["arguments"] == ["name"]
    assert function["start_line"] == 2
    assert function["end_line"] == 3


def test_parse_class_and_methods():
    source = """
class Student:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return self.name
"""

    result = parse_python_file(source, "student.py")

    assert result["status"] == "success"
    assert result["total_symbols"] == 3

    class_symbol = result["symbols"][0]
    init_method = result["symbols"][1]
    greet_method = result["symbols"][2]

    assert class_symbol["name"] == "Student"
    assert class_symbol["type"] == "class"

    assert init_method["name"] == "__init__"
    assert init_method["type"] == "method"
    assert init_method["parent_class"] == "Student"
    assert init_method["arguments"] == ["self", "name"]

    assert greet_method["name"] == "greet"
    assert greet_method["type"] == "method"
    assert greet_method["parent_class"] == "Student"


def test_parse_nested_function():
    source = """
def outer():
    def inner():
        return 10

    return inner()
"""

    result = parse_python_file(source)

    assert result["total_symbols"] == 2

    outer = result["symbols"][0]
    inner = result["symbols"][1]

    assert outer["name"] == "outer"
    assert outer["type"] == "function"

    assert inner["name"] == "inner"
    assert inner["type"] == "nested_function"
    assert inner["parent_function"] == "outer"


def test_parse_async_function():
    source = """
async def fetch_data(url):
    return url
"""

    result = parse_python_file(source)

    assert result["status"] == "success"
    assert result["total_symbols"] == 1

    function = result["symbols"][0]

    assert function["name"] == "fetch_data"
    assert function["type"] == "function"
    assert function["arguments"] == ["url"]


def test_parse_decorated_function():
    source = """
@staticmethod
def calculate(value):
    return value * 2
"""

    result = parse_python_file(source)

    function = result["symbols"][0]

    assert function["name"] == "calculate"
    assert function["start_line"] == 2
    assert function["end_line"] == 4


def test_parse_invalid_python_syntax():
    source = """
def broken_function(
    print("Missing closing parenthesis")
"""

    result = parse_python_file(source, "broken.py")

    assert result["status"] == "failed"
    assert result["total_symbols"] == 0
    assert result["symbols"] == []
    assert result["error"] is not None
    assert result["error"]["line"] is not None


def test_parse_file_without_symbols():
    source = """
name = "RepoLens"
version = 1
"""

    result = parse_python_file(source, "config.py")

    assert result["status"] == "success"
    assert result["total_symbols"] == 0
    assert result["symbols"] == []
    assert result["error"] is None


def test_extract_original_source_code():
    source = """def add(a, b):
    return a + b
"""

    result = parse_python_file(source, "math_utils.py")

    function = result["symbols"][0]

    assert function["source"] == source.strip()
    assert function["start_line"] == 1
    assert function["end_line"] == 2
    assert function["parent_class"] is None
def test_parse_advanced_function_arguments():
    source = """
def process(a, b, *args, option=True, **kwargs):
    pass
"""

    result = parse_python_file(source)

    function = result["symbols"][0]

    assert function["arguments"] == [
        "a",
        "b",
        "*args",
        "option",
        "**kwargs",
    ]
def test_parse_nested_classes():
    source = """
class Outer:
    class Inner:
        def execute(self):
            pass
"""

    result = parse_python_file(source)

    assert result["total_symbols"] == 3

    outer = result["symbols"][0]
    inner = result["symbols"][1]
    method = result["symbols"][2]

    assert outer["type"] == "class"
    assert outer["name"] == "Outer"

    assert inner["type"] == "class"
    assert inner["name"] == "Inner"
    assert inner["parent_class"] == "Outer"

    assert method["type"] == "method"
    assert method["name"] == "execute"
    assert method["parent_class"] == "Inner"