
import ast


def get_function_arguments(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Extract function argument names."""

    arguments = node.args

    result = []

    # Positional-only and regular arguments
    result.extend(arg.arg for arg in arguments.posonlyargs)
    result.extend(arg.arg for arg in arguments.args)

    # *args
    if arguments.vararg:
        result.append(f"*{arguments.vararg.arg}")

    # Keyword-only arguments
    result.extend(arg.arg for arg in arguments.kwonlyargs)

    # **kwargs
    if arguments.kwarg:
        result.append(f"**{arguments.kwarg.arg}")

    return result


class PythonStructureVisitor(ast.NodeVisitor):
    """Extract classes, functions, and methods from Python AST."""

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.symbols = []
        self.class_stack = []
        self.function_stack = []

    def get_source(self, node: ast.AST) -> str:
        """Return the original source code for an AST node."""

        return ast.get_source_segment(self.source_code, node) or ""

    def get_start_line(self, node: ast.AST) -> int:
        """Include decorator lines when present."""

        decorator_lines = [
            decorator.lineno
            for decorator in getattr(node, "decorator_list", [])
        ]

        return min([node.lineno] + decorator_lines)

    def visit_ClassDef(self, node: ast.ClassDef):
        """Extract class definitions."""

        symbol = {
            "type": "class",
            "name": node.name,
            "parent_class": self.class_stack[-1] if self.class_stack else None,
            "parent_function": self.function_stack[-1] if self.function_stack else None,
            "arguments": [],
            "start_line": self.get_start_line(node),
            "end_line": node.end_lineno,
            "source": self.get_source(node),
        }

        self.symbols.append(symbol)

        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_function(node)

    def _visit_function(self, node):
        """Extract functions, methods, and nested functions."""

        if self.class_stack and not self.function_stack:
            symbol_type = "method"
        elif self.function_stack:
            symbol_type = "nested_function"
        else:
            symbol_type = "function"

        symbol = {
            "type": symbol_type,
            "name": node.name,
            "parent_class": self.class_stack[-1] if self.class_stack else None,
            "parent_function": self.function_stack[-1] if self.function_stack else None,
            "arguments": get_function_arguments(node),
            "start_line": self.get_start_line(node),
            "end_line": node.end_lineno,
            "source": self.get_source(node),
        }

        self.symbols.append(symbol)

        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()


def parse_python_file(source_code: str, file_path: str = "") -> dict:
    """
    Parse Python source code and extract its structural elements.

    Returns classes, functions, methods, and nested functions
    with their source code and line numbers.
    """

    try:
        tree = ast.parse(source_code, filename=file_path or "<unknown>")

        visitor = PythonStructureVisitor(source_code)
        visitor.visit(tree)

        return {
            "status": "success",
            "language": "Python",
            "file_path": file_path,
            "total_symbols": len(visitor.symbols),
            "symbols": visitor.symbols,
            "error": None,
        }

    except SyntaxError as error:
        return {
            "status": "failed",
            "language": "Python",
            "file_path": file_path,
            "total_symbols": 0,
            "symbols": [],
            "error": {
                "message": error.msg,
                "line": error.lineno,
                "column": error.offset,
            },
        }
