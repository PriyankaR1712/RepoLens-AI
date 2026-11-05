
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RepositoryCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=255
    )

    source_type: Literal["github", "zip"]

    source_url: str | None = Field(
        default=None,
        max_length=2048
    )

    @model_validator(mode="after")
    def validate_source(self):
        self.name = self.name.strip()

        if not self.name:
            raise ValueError("Repository name cannot be empty")

        if self.source_type == "github" and not self.source_url:
            raise ValueError("GitHub repositories require a source URL")

        if self.source_type == "zip" and self.source_url is not None:
            raise ValueError("ZIP uploads should not have a source URL")

        return self


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    source_type: str
    source_url: str | None
    status: str
    created_at: datetime
    updated_at: datetime
