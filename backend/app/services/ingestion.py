import asyncio

from starlette.concurrency import run_in_threadpool

from app.database.documents import require_patient
from app.exceptions import AppError
from app.observability import stage
from app.services.chunking import ChunkingService
from app.services.embeddings import validate_vectors


class IngestionService:
    def __init__(self, privacy, embeddings, chunks, settings):
        self.privacy = privacy
        self.embeddings = embeddings
        self.chunks = chunks
        self.settings = settings
        self.chunking = ChunkingService(settings)

    async def ingest(self, patient_id: str, document: dict, text: str) -> int:
        require_patient(patient_id)
        if document.get("patient_id") != patient_id:
            raise AppError("OWNERSHIP_MISMATCH", "Document ownership is invalid.", 403)
        # Enforced here as well as at the upload boundary, before any provider sees text.
        with stage("privacy"):
            sanitized = await run_in_threadpool(self.privacy.sanitize, text)
        with stage("chunking"):
            texts = await run_in_threadpool(self.chunking.split, sanitized)
        if not texts:
            raise AppError("EMPTY_DOCUMENT", "Document has no usable text.")
        vectors = []
        for offset in range(0, len(texts), self.settings.embedding_batch_size):
            batch = texts[offset : offset + self.settings.embedding_batch_size]
            try:
                with stage("embedding"):
                    values = await asyncio.wait_for(
                        self.embeddings.embed_documents(batch), self.settings.embedding_timeout_seconds
                    )
            except AppError:
                raise
            except Exception as exc:
                raise AppError("EMBEDDING_UNAVAILABLE", "Embedding service is unavailable.", 503) from exc
            validate_vectors(values, len(batch), self.settings.embedding_dimensions)
            vectors.extend(values)
        records = self.chunking.records(patient_id, document, texts, vectors)
        try:
            with stage("vector_persistence"):
                await self.chunks.insert(patient_id, records)
        except Exception:
            await self.chunks.delete_document(patient_id, document["_id"])
            raise
        return len(records)

    async def remove(self, patient_id: str, document_id: str) -> None:
        await self.chunks.delete_document(patient_id, document_id)
