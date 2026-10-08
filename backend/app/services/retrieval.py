import asyncio
import math

from app.database.documents import require_patient
from app.exceptions import AppError
from app.observability import stage
from app.services.embeddings import validate_vectors


class RetrievalService:
    def __init__(self, chunks, documents, embeddings, settings):
        self.chunks = chunks
        self.documents = documents
        self.embeddings = embeddings
        self.settings = settings

    async def retrieve_summary(self, patient_id: str, document_type=None) -> list[dict]:
        require_patient(patient_id)
        rows = await self.chunks.summary_rows(patient_id, document_type)
        if len(rows) > 1000:
            raise AppError(
                "SUMMARY_TOO_LARGE",
                "Too many records for one summary. Select a document type or ask a narrower question.",
                422,
            )
        verified = []
        documents = {}
        for row in rows:
            if row.get("patient_id") != patient_id:
                raise AppError("ISOLATION_VIOLATION", "Record isolation validation failed.", 503)
            document_id = row["document_id"]
            if document_id not in documents:
                documents[document_id] = await self.documents.get(patient_id, document_id)
            document = documents[document_id]
            if document is None or document["processing_status"] != "completed":
                continue
            if row["document_type"] != document["document_type"] or (
                document_type is not None and row["document_type"] != document_type
            ):
                raise AppError("SOURCE_MISMATCH", "Record source validation failed.", 503)
            verified.append(row)
        if (
            sum(len(r["text"]) for r in verified) > self.settings.max_context_chars
            or len({r["document_id"] for r in verified}) > 30
        ):
            raise AppError(
                "SUMMARY_TOO_LARGE",
                "Records exceed the summary limit. Select a document type or ask a narrower question.",
                422,
            )
        return verified

    async def retrieve(self, patient_id: str, query: str, document_type=None) -> list[dict]:
        require_patient(patient_id)
        try:
            with stage("embedding"):
                vector = await asyncio.wait_for(
                    self.embeddings.embed_text(query), self.settings.embedding_timeout_seconds
                )
        except AppError:
            raise
        except Exception as exc:
            raise AppError("EMBEDDING_UNAVAILABLE", "Embedding service is unavailable.", 503) from exc
        validate_vectors([vector], 1, self.settings.embedding_dimensions)
        with stage("vector_search"):
            rows = await self.chunks.search(patient_id, vector, self.settings, document_type)
        verified = []
        for row in rows:
            if row.get("patient_id") != patient_id:
                raise AppError("ISOLATION_VIOLATION", "Record isolation validation failed.", 503)
            document = await self.documents.get(patient_id, row["document_id"])
            if document is None or document["processing_status"] != "completed":
                continue
            if row["document_type"] != document["document_type"] or (
                document_type is not None and row["document_type"] != document_type
            ):
                raise AppError("SOURCE_MISMATCH", "Record source validation failed.", 503)
            score = row.get("score")
            if not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 1:
                raise AppError("INVALID_SEARCH_RESULT", "Search returned invalid scores.", 503)
            verified.append(row)
        return verified
