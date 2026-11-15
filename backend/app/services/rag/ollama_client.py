"""Small standard-library client for Ollama's local generate API."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OllamaError(RuntimeError):
    """Raised when Ollama cannot produce a valid response."""


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url = (
            base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2:1b")
        timeout_value = timeout if timeout is not None else float(
            os.getenv("OLLAMA_TIMEOUT", "120")
        )
        if not self.base_url:
            raise ValueError("Ollama base URL cannot be empty.")
        if not self.model.strip():
            raise ValueError("Ollama model cannot be empty.")
        if timeout_value <= 0:
            raise ValueError("Ollama timeout must be greater than zero.")
        self.timeout = timeout_value

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string.")

        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }).encode("utf-8")
        request = Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except UnicodeDecodeError as exc:
            raise OllamaError("Ollama response was not valid UTF-8.") from exc
        except HTTPError as exc:
            try:
                error_body = exc.read().decode("utf-8")
                details = json.loads(error_body).get("error", error_body)
            except (UnicodeDecodeError, json.JSONDecodeError):
                details = str(exc.reason)
            raise OllamaError(f"Ollama returned HTTP {exc.code}: {details}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise OllamaError(f"Ollama is unavailable: {exc}") from exc

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama returned malformed JSON.") from exc

        if not isinstance(data, dict):
            raise OllamaError("Ollama returned an invalid response.")
        if data.get("error"):
            raise OllamaError(str(data["error"]))
        answer = data.get("response")
        if not isinstance(answer, str) or not answer.strip():
            raise OllamaError("Ollama response did not contain an answer.")
        return answer.strip()
