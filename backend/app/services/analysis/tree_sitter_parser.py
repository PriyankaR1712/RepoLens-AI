
from tree_sitter_language_pack import get_parser


# Map our supported languages to Tree-sitter grammar names.
LANGUAGE_GRAMMARS = {
    "JavaScript": "javascript",
    "TypeScript": "typescript",
    "TSX": "tsx",
    "Java": "java",
}


# Node types representing classes.
CLASS_NODE_TYPES = {
    "class_declaration",
    "abstract_class_declaration",
    "class",
}

# Node types representing functions.
FUNCTION_NODE_TYPES = {
    "function_declaration",
    "generator_function_declaration",
    "function_expression",
    "arrow_function",
    "method_definition",
    "method_declaration",
    "constructor_declaration",
}

# Node types representing interfaces and other class-like structures.
INTERFACE_NODE_TYPES = {
    "interface_declaration",
    "enum_declaration",
    "record_declaration",
    "type_alias_declaration",
}


class TreeSitterStructureVisitor:
    """Extract code structures from a Tree-sitter syntax tree."""

    def __init__(self, source_code: str, language: str):
        self.source_code = source_code
        self.source_bytes = source_code.encode("utf-8")
        self.language = language
        self.symbols = []
        self.class_stack = []
        self.function_stack = []

    def get_source(self, node) -> str:
        """Extract the original source code represented by a node."""

        return self.source_bytes[
            node.start_byte:node.end_byte
        ].decode("utf-8")

    def get_node_text(self, node) -> str | None:
        """Extract text from a node, if available."""

        if node is None:
            return None

        return self.get_source(node)

    def get_name(self, node) -> str:
        """Extract a symbol name from its name field."""

        name_node = node.child_by_field_name("name")

        if name_node is not None:
            return self.get_node_text(name_node)

        # Handle JavaScript/TypeScript variable declarations
        # such as const greet = () => {}.
        parent = node.parent

        if parent and parent.type == "variable_declarator":
            name_node = parent.child_by_field_name("name")

            if name_node:
                return self.get_node_text(name_node)

        return "<anonymous>"

    def get_arguments(self, node) -> list[str]:
        """Extract function or method parameter names."""

        parameters = node.child_by_field_name("parameters")

        if parameters is None:
            return []

        arguments = []

        for child in parameters.named_children:
            if child.type in {
                "required_parameter",
                "optional_parameter",
            }:
                pattern = child.child_by_field_name("pattern")
                if pattern:
                    arguments.append(self.get_node_text(pattern))
                else:
                    arguments.append(self.get_source(child))

            elif child.type == "spread_parameter":
                arguments.append(self.get_source(child))

            else:
                arguments.append(self.get_source(child))

        return arguments

    def add_symbol(self, node, symbol_type: str):
        """Create a normalized symbol record."""

        symbol = {
            "type": symbol_type,
            "name": self.get_name(node),
            "parent_class": (
                self.class_stack[-1] if self.class_stack else None
            ),
            "parent_function": (
                self.function_stack[-1] if self.function_stack else None
            ),
            "arguments": (
                self.get_arguments(node)
                if symbol_type in {"function", "method", "nested_function"}
                else []
            ),
            "start_line": node.start_point.row + 1,
            "end_line": node.end_point.row + 1,
            "source": self.get_source(node),
        }

        self.symbols.append(symbol)

    def visit(self, node):
        """Recursively visit syntax tree nodes."""

        if node.type in CLASS_NODE_TYPES:
            self.add_symbol(node, "class")

            class_name = self.get_name(node)
            self.class_stack.append(class_name)

            for child in node.named_children:
                self.visit(child)

            self.class_stack.pop()
            return

        if node.type in INTERFACE_NODE_TYPES:
            self.add_symbol(node, "class")

            class_name = self.get_name(node)
            self.class_stack.append(class_name)

            for child in node.named_children:
                self.visit(child)

            self.class_stack.pop()
            return

        if node.type in FUNCTION_NODE_TYPES:
            if self.class_stack and not self.function_stack:
                symbol_type = "method"
            elif self.function_stack:
                symbol_type = "nested_function"
            else:
                symbol_type = "function"

            self.add_symbol(node, symbol_type)

            function_name = self.get_name(node)
            self.function_stack.append(function_name)

            for child in node.named_children:
                self.visit(child)

            self.function_stack.pop()
            return

        for child in node.named_children:
            self.visit(child)


def parse_tree_sitter_file(
    source_code: str,
    language: str,
    file_path: str = "",
) -> dict:
    """
    Parse JavaScript, TypeScript, TSX, or Java source code.

    Extracts classes, interfaces, functions, methods,
    arguments, source code, and line numbers.
    """

    if language not in LANGUAGE_GRAMMARS:
        return {
            "status": "failed",
            "language": language,
            "file_path": file_path,
            "total_symbols": 0,
            "symbols": [],
            "error": {
                "message": f"Unsupported Tree-sitter language: {language}",
                "line": None,
                "column": None,
            },
        }

    try:
        parser = get_parser(LANGUAGE_GRAMMARS[language])
        source_bytes = source_code.encode("utf-8")
        tree = parser.parse(source_bytes)

        root = tree.root_node

        visitor = TreeSitterStructureVisitor(
            source_code=source_code,
            language=language,
        )
        visitor.visit(root)

        error_node = None

        if root.has_error:
            stack = [root]

            while stack:
                current = stack.pop()

                if current.type == "ERROR" or current.is_missing:
                    error_node = current
                    break

                stack.extend(reversed(current.children))

        if error_node:
            error = {
                "message": "Tree-sitter detected invalid or incomplete syntax.",
                "line": error_node.start_point.row + 1,
                "column": error_node.start_point.column + 1,
            }
        else:
            error = None

        return {
            "status": "success" if error is None else "partial",
            "language": language,
            "file_path": file_path,
            "total_symbols": len(visitor.symbols),
            "symbols": visitor.symbols,
            "error": error,
        }

    except Exception as error:
        return {
            "status": "failed",
            "language": language,
            "file_path": file_path,
            "total_symbols": 0,
            "symbols": [],
            "error": {
                "message": str(error),
                "line": None,
                "column": None,
            },
        }
