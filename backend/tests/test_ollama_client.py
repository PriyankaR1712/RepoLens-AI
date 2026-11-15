import json
from io import BytesIO
from urllib.error import HTTPError, URLError
from unittest.mock import Mock

import pytest

from app.services.rag.ollama_client import OllamaClient, OllamaError


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


def test_ollama_client_posts_prompt_and_returns_answer(monkeypatch):
    urlopen = Mock(return_value=FakeResponse(b'{"response":"  grounded answer  "}'))
    monkeypatch.setattr("app.services.rag.ollama_client.urlopen", urlopen)
    client = OllamaClient("http://localhost:11434/", "qwen2.5-coder", 30)

    answer = client.generate("Use this context")

    assert answer == "grounded answer"
    request = urlopen.call_args.args[0]
    assert request.full_url == "http://localhost:11434/api/generate"
    assert json.loads(request.data) == {
        "model": "qwen2.5-coder",
        "prompt": "Use this context",
        "stream": False,
    }
    assert urlopen.call_args.kwargs["timeout"] == 30


@pytest.mark.parametrize(
    "body",
    [b"not json", b"[]", b"{}", b'{"error":"model not found"}'],
)
def test_ollama_client_rejects_malformed_or_error_responses(monkeypatch, body):
    monkeypatch.setattr(
        "app.services.rag.ollama_client.urlopen",
        lambda *_args, **_kwargs: FakeResponse(body),
    )

    with pytest.raises(OllamaError):
        OllamaClient().generate("Question")


def test_ollama_client_reports_unavailable_server(monkeypatch):
    def fail(*_args, **_kwargs):
        raise URLError("connection refused")

    monkeypatch.setattr("app.services.rag.ollama_client.urlopen", fail)
    with pytest.raises(OllamaError, match="unavailable"):
        OllamaClient().generate("Question")


def test_ollama_client_reads_configuration_from_environment(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.internal:11434/")
    monkeypatch.setenv("OLLAMA_MODEL", "code-model")
    monkeypatch.setenv("OLLAMA_TIMEOUT", "45")

    client = OllamaClient()

    assert client.base_url == "http://ollama.internal:11434"
    assert client.model == "code-model"
    assert client.timeout == 45


def test_ollama_client_defaults_to_installed_model(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)

    assert OllamaClient().model == "llama3.2:1b"


def test_ollama_client_reports_invalid_utf8(monkeypatch):
    monkeypatch.setattr(
        "app.services.rag.ollama_client.urlopen",
        lambda *_args, **_kwargs: FakeResponse(b"\xff"),
    )

    with pytest.raises(OllamaError, match="UTF-8"):
        OllamaClient().generate("Question")


def test_ollama_client_reports_http_model_error(monkeypatch):
    error = HTTPError(
        "http://localhost:11434/api/generate",
        404,
        "Not Found",
        {},
        BytesIO(b'{"error":"model not found"}'),
    )
    monkeypatch.setattr(
        "app.services.rag.ollama_client.urlopen",
        Mock(side_effect=error),
    )
    with pytest.raises(OllamaError, match="model not found"):
        OllamaClient().generate("Question")
