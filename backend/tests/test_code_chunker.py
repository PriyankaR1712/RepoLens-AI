
from app.services.chunking.code_chunker import chunk_parsed_file


def make_parsed_result(symbols, source=None, status="success"):
    result = {
        "status": status,
        "language": "Python",
        "file_path": "example.py",
        "total_symbols": len(symbols),
        "symbols": symbols,
    }

    if source is not None:
        result["source"] = source

    return result


def make_symbol(
    symbol_type,
    name,
    source,
    start_line,
    end_line,
    parent_class=None,
    parent_function=None,
):
    return {
        "type": symbol_type,
        "name": name,
        "parent_class": parent_class,
        "parent_function": parent_function,
        "arguments": [],
        "start_line": start_line,
        "end_line": end_line,
        "source": source,
    }


def test_standalone_function_creates_one_chunk():
    function = make_symbol(
        "function",
        "multiply",
        "def multiply(a, b):\n    return a * b",
        1,
        2,
    )

    chunks = chunk_parsed_file(make_parsed_result([function]))

    assert len(chunks) == 1
    assert chunks[0]["symbol_name"] == "multiply"
    assert chunks[0]["symbol_type"] == "function"
    assert chunks[0]["start_line"] == 1
    assert chunks[0]["end_line"] == 2
    assert chunks[0]["content"] == function["source"]


def test_class_and_methods_do_not_create_duplicate_chunks():
    class_symbol = make_symbol(
        "class",
        "Calculator",
        (
            "class Calculator:\n"
            "    def add(self, a, b):\n"
            "        return a + b"
        ),
        1,
        3,
    )

    method_symbol = make_symbol(
        "method",
        "add",
        "def add(self, a, b):\n    return a + b",
        2,
        3,
        parent_class="Calculator",
    )

    chunks = chunk_parsed_file(
        make_parsed_result([class_symbol, method_symbol])
    )

    assert len(chunks) == 1
    assert chunks[0]["symbol_name"] == "Calculator"
    assert chunks[0]["symbol_type"] == "class"
    assert "def add" in chunks[0]["content"]


def test_multiple_functions_preserve_original_line_numbers():
    first = make_symbol(
        "function",
        "first",
        "def first():\n    return 1",
        2,
        3,
    )

    second = make_symbol(
        "function",
        "second",
        "def second():\n    return 2",
        7,
        8,
    )

    chunks = chunk_parsed_file(
        make_parsed_result([second, first])
    )

    assert len(chunks) == 2
    assert chunks[0]["symbol_name"] == "first"
    assert chunks[1]["symbol_name"] == "second"
    assert chunks[0]["start_line"] == 2
    assert chunks[1]["start_line"] == 7


def test_oversized_function_is_split_into_multiple_chunks():
    source = (
        "def example():\n"
        "    first = 1\n"
        "    second = 2\n"
        "    third = 3\n"
        "    fourth = 4\n"
    )

    function = make_symbol(
        "function",
        "example",
        source,
        10,
        14,
    )

    chunks = chunk_parsed_file(
        make_parsed_result([function]),
        max_chunk_size=25,
    )

    assert len(chunks) > 1
    assert chunks[0]["start_line"] == 10
    assert chunks[-1]["end_line"] == 14

    combined_content = "".join(
        chunk["content"] for chunk in chunks
    )

    assert combined_content == source


def test_chunk_indices_are_sequential():
    first = make_symbol(
        "function",
        "first",
        "def first():\n    return 1",
        1,
        2,
    )

    second = make_symbol(
        "function",
        "second",
        "def second():\n    return 2",
        4,
        5,
    )

    chunks = chunk_parsed_file(
        make_parsed_result([first, second])
    )

    assert [chunk["chunk_index"] for chunk in chunks] == [0, 1]


def test_failed_parser_result_returns_no_chunks():
    result = make_parsed_result(
        [],
        status="failed",
    )

    assert chunk_parsed_file(result) == []


def test_file_without_symbols_preserves_available_source():
    source = "# Configuration file\nDEBUG = True\n"

    result = make_parsed_result(
        [],
        source=source,
    )

    chunks = chunk_parsed_file(result)

    assert len(chunks) == 1
    assert chunks[0]["symbol_type"] == "file"
    assert chunks[0]["content"] == source
    assert chunks[0]["start_line"] == 1
    assert chunks[0]["end_line"] == 2


def test_invalid_max_chunk_size_is_rejected():
    result = make_parsed_result([])

    try:
        chunk_parsed_file(result, max_chunk_size=0)
        assert False, "Expected ValueError"
    except ValueError:
        pass
def test_oversized_class_is_split_into_method_chunks():
    class_source = (
        "class BankAccount:\n"
        "    balance = 0\n"
        "\n"
        "    def deposit(self, amount):\n"
        "        self.balance += amount\n"
        "        return self.balance\n"
        "\n"
        "    def withdraw(self, amount):\n"
        "        self.balance -= amount\n"
        "        return self.balance\n"
    )

    class_symbol = make_symbol(
        "class",
        "BankAccount",
        class_source,
        1,
        10,
    )

    deposit_method = make_symbol(
        "method",
        "deposit",
        (
            "    def deposit(self, amount):\n"
            "        self.balance += amount\n"
            "        return self.balance"
        ),
        4,
        6,
        parent_class="BankAccount",
    )

    withdraw_method = make_symbol(
        "method",
        "withdraw",
        (
            "    def withdraw(self, amount):\n"
            "        self.balance -= amount\n"
            "        return self.balance"
        ),
        8,
        10,
        parent_class="BankAccount",
    )

    result = make_parsed_result(
        [class_symbol, deposit_method, withdraw_method]
    )

    chunks = chunk_parsed_file(
        result,
        max_chunk_size=120,
    )

    method_chunks = [
        chunk for chunk in chunks
        if chunk["symbol_type"] == "method"
    ]

    assert len(method_chunks) == 2
    context_chunks = [
        chunk for chunk in chunks
        if chunk["symbol_type"] == "class_context"
    ]

    assert len(context_chunks) >= 1

    context_content = "".join(
        chunk["content"] for chunk in context_chunks
    )

    assert "class BankAccount:" in context_content
    assert "balance = 0" in context_content
    assert {
        chunk["symbol_name"] for chunk in method_chunks
    } == {"deposit", "withdraw"}

    assert all(
        chunk["parent_class"] == "BankAccount"
        for chunk in method_chunks
    )

    assert all(
        chunk["start_line"] >= 1
        and chunk["end_line"] >= chunk["start_line"]
        for chunk in chunks
    )
def test_oversized_method_preserves_parent_class_and_line_numbers():
    method_source = (
        "    def calculate(self):\n"
        "        first = 10\n"
        "        second = 20\n"
        "        third = 30\n"
        "        return first + second + third"
    )

    method = make_symbol(
        "method",
        "calculate",
        method_source,
        5,
        9,
        parent_class="Calculator",
    )

    class_symbol = make_symbol(
        "class",
        "Calculator",
        (
            "class Calculator:\n"
            "    pass\n"
        ),
        1,
        2,
    )

    result = make_parsed_result([class_symbol, method])

    # The class is small, so this test needs a large class source
    # to exercise the oversized-class splitting path.
    class_symbol["source"] = (
        "class Calculator:\n"
        "    pass\n"
        + "\n" * 3
        + method_source
        + "\n"
    )
    class_symbol["end_line"] = 10

    chunks = chunk_parsed_file(result, max_chunk_size=40)

    method_chunks = [
        chunk for chunk in chunks
        if chunk["symbol_type"] == "method"
    ]

    assert len(method_chunks) > 1

    assert all(
        chunk["parent_class"] == "Calculator"
        for chunk in method_chunks
    )

    assert method_chunks[0]["start_line"] == 5
    assert method_chunks[-1]["end_line"] == 9

    assert [
        chunk["chunk_index"] for chunk in chunks
    ] == list(range(len(chunks)))