import math
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.documents import DocumentType


class Chunk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunk_id: str = Field(pattern=r"^CHUNK_[a-f0-9]{32}$")
    document_id: str = Field(pattern=r"^DOC_[a-f0-9]{32}$")
    patient_id: str = Field(pattern=r"^PAT_[a-f0-9]{32}$")
    document_type: DocumentType
    document_date: str | None
    source: str = Field(min_length=1)
    chunk_index: int = Field(ge=0)
    text: str = Field(min_length=1)
    embedding: list[float] = Field(min_length=1)
    created_at: datetime

    @field_validator("embedding")
    @classmethod
    def finite_embedding(cls, values):
        if not all(math.isfinite(v) for v in values) or not any(v != 0 for v in values):
            raise ValueError("Embedding must be finite and nonzero")
        return values

    def mongo_record(self) -> dict:
        record = self.model_dump()
        record["_id"] = record.pop("chunk_id")
        return record
