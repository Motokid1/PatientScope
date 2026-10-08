from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.documents import DocumentType


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=2000)
    document_type: DocumentType | None = None

    @field_validator("question")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Question must not be blank")
        return value.strip()


class Source(BaseModel):
    document_id: str
    document_type: DocumentType
    document_date: date | None


class ChatResponse(BaseModel):
    answer: str
    status: Literal["answered", "insufficient_context"]
    sources: list[Source]
    request_id: str
