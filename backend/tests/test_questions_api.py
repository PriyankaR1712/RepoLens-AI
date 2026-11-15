from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.api.questions import ask_repository
from app.models.repository import Repository
from app.schemas.question import QuestionRequest
from app.services.rag.ollama_client import OllamaError
from app.services.rag.rag_service import NoRelevantContextError


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *_args):
        return self

    def first(self):
        return self.result


class FakeDatabase:
    def __init__(self, repository):
        self.repository = repository

    def query(self, _model):
        return FakeQuery(self.repository)


def _repository(status="indexed"):
    return SimpleNamespace(id=17, status=status)


def test_question_api_returns_answer_and_sources():
    service = Mock()
    service.ask.return_value = {
        "repository_id": "17",
        "answer": "It validates credentials.",
        "sources": [{
            "file_path": "auth.py",
            "symbol_name": "authenticate",
            "start_line": 4,
            "end_line": 8,
            "snippet": "def authenticate(): pass",
        }],
    }

    response = ask_repository(
        17, QuestionRequest(question="What does auth do?"),
        FakeDatabase(_repository()), service,
    )

    service.ask.assert_called_once_with("17", "What does auth do?")
    assert response["answer"] == "It validates credentials."
    assert response["sources"][0]["file_path"] == "auth.py"


def test_question_api_returns_404_for_unknown_repository():
    with pytest.raises(HTTPException) as error:
        ask_repository(
            17, QuestionRequest(question="Question"),
            FakeDatabase(None), Mock(),
        )
    assert error.value.status_code == 404


def test_question_api_returns_409_for_repository_not_indexed():
    with pytest.raises(HTTPException) as error:
        ask_repository(
            17, QuestionRequest(question="Question"),
            FakeDatabase(_repository("indexing")), Mock(),
        )
    assert error.value.status_code == 409


def test_question_api_returns_404_when_retrieval_is_empty():
    service = Mock()
    service.ask.side_effect = NoRelevantContextError("No relevant code")
    with pytest.raises(HTTPException) as error:
        ask_repository(
            17, QuestionRequest(question="Question"),
            FakeDatabase(_repository()), service,
        )
    assert error.value.status_code == 404


def test_question_api_returns_503_when_ollama_is_unavailable():
    service = Mock()
    service.ask.side_effect = OllamaError("connection refused")
    with pytest.raises(HTTPException) as error:
        ask_repository(
            17, QuestionRequest(question="Question"),
            FakeDatabase(_repository()), service,
        )
    assert error.value.status_code == 503


def test_question_api_returns_500_for_retrieval_failure():
    service = Mock()
    service.ask.side_effect = RuntimeError("embedding failed")
    with pytest.raises(HTTPException) as error:
        ask_repository(
            17, QuestionRequest(question="Question"),
            FakeDatabase(_repository()), service,
        )
    assert error.value.status_code == 500


def test_question_request_rejects_blank_text():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        QuestionRequest(question="   ")
