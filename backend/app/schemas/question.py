from typing import Any

from pydantic import BaseModel, Field, field_validator


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question cannot be blank.")
        return value


class Citation(BaseModel):
    file_path: str
    symbol_name: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    snippet: str


class QuestionResponse(BaseModel):
    repository_id: str
    answer: str
    sources: list[Citation]
