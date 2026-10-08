from dataclasses import dataclass
from typing import TypedDict

from app.schemas.documents import DocumentType


@dataclass(frozen=True)
class AuthContext:
    patient_id: str
    request_id: str


class RAGState(TypedDict):
    patient_id: str
    request_id: str
    original_query: str
    current_query: str
    query_category: str | None
    document_type: DocumentType | None
    retrieved_chunks: list[dict]
    relevant_chunks: list[dict]
    relevance_passed: bool
    retry_count: int
    generation_count: int
    generated_answer: dict | None
    context: list[dict]
    validation_passed: bool
    validation_issues: list[str]
    final_answer: str | None
    status: str
