from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.documents import DocumentType


class GenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    answer: str = Field(min_length=1, max_length=6000)
    source_ids: list[str] = Field(max_length=30)


class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query_category: Literal[
        "medication",
        "lab_result",
        "diagnosis",
        "claim",
        "procedure",
        "clinical_summary",
        "appointment",
        "general_clinical",
        "unknown",
    ]
    document_type: DocumentType | None
    confidence: float = Field(ge=0, le=1)


class RelevanceResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    relevant: bool
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(max_length=500)


class RewriteResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    rewritten_query: str = Field(min_length=1, max_length=2000)
    preserves_intent: bool


class IntentResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    passed: bool


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    passed: bool
    issues: list[str] = Field(max_length=20)
