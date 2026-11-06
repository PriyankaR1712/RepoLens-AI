from app.services.analysis.tree_sitter_parser import (
    parse_tree_sitter_file,
)

from app.services.chunking.code_chunker import chunk_parsed_file


SAMPLES = [
    {
        "language": "JavaScript",
        "file_path": "calculator.js",
        "source": """
const multiply = (a, b) => a * b;

class Calculator {
    add(a, b) {
        return a + b;
    }
}
""",
        "expected_names": {"multiply", "Calculator", "add"},
    },
    {
        "language": "TypeScript",
        "file_path": "user.ts",
        "source": """
interface User {
    name: string;
    age: number;
}

class UserService {
    getUser(id: number): User {
        return { name: "Alex", age: id };
    }
}
""",
        "expected_names": {"User", "UserService", "getUser"},
    },
    {
        "language": "TSX",
        "file_path": "Welcome.tsx",
        "source": """
type Props = {
    name: string;
};

function Welcome({ name }: Props) {
    return <h1>Hello, {name}!</h1>;
}

export default Welcome;
""",
        "expected_names": {"Props", "Welcome"},
    },
    {
        "language": "Java",
        "file_path": "BankAccount.java",
        "source": """
public class BankAccount {
    private double balance;

    public BankAccount(double balance) {
        this.balance = balance;
    }

    public double deposit(double amount) {
        balance += amount;
        return balance;
    }
}
""",
        "expected_names": {
            "BankAccount",
            "deposit",
        },
    },
]


def test_parse_realistic_source_samples():
    for sample in SAMPLES:
        result = parse_tree_sitter_file(
            source_code=sample["source"],
            language=sample["language"],
            file_path=sample["file_path"],
        )

        assert result["status"] == "success", (
            f"{sample['language']} failed: {result['error']}"
        )

        assert result["file_path"] == sample["file_path"]

        actual_names = {
            symbol["name"] for symbol in result["symbols"]
        }

        missing_names = (
            sample["expected_names"] - actual_names
        )

        assert not missing_names, (
            f"{sample['language']} is missing symbols: "
            f"{missing_names}. Found: {actual_names}"
        )

        for symbol in result["symbols"]:
            assert symbol["start_line"] >= 1
            assert symbol["end_line"] >= symbol["start_line"]
            assert symbol["source"]