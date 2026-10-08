from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

DocumentType = Literal[
    "prescription",
    "lab_report",
    "clinical_note",
    "claim_document",
    "diagnostic_report",
    "discharge_summary",
    "other",
]


class DocumentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str
    document_type: DocumentType
    document_date: date | None
    filename: str
    processing_status: Literal["uploaded", "processing", "completed", "failed"]
    chunk_count: int
    created_at: datetime


class DocumentList(BaseModel):
    documents: list[DocumentResponse]
