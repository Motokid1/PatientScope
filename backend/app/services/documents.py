from datetime import datetime, timezone
from uuid import uuid4

from starlette.concurrency import run_in_threadpool

from app.exceptions import AppError
from app.observability import stage
from app.schemas.documents import DocumentResponse
from app.services.classification import classify_document
from app.services.extraction import ExtractionService


def public_document(row: dict) -> DocumentResponse:
    return DocumentResponse(
        document_id=row["_id"],
        document_type=row["document_type"],
        document_date=row["document_date"],
        filename=row["original_filename"],
        processing_status=row["processing_status"],
        chunk_count=row["chunk_count"],
        created_at=row["created_at"],
    )


class DocumentService:
    def __init__(self, repository, settings, ingestion=None, privacy=None):
        self.repository = repository
        self.settings = settings
        self.extraction = ExtractionService(settings.max_extracted_chars)
        self.ingestion = ingestion
        self.privacy = privacy

    async def upload(self, patient_id: str, upload, document_type, document_date) -> DocumentResponse:
        limit = self.settings.max_upload_size_mb * 1024 * 1024
        content = bytearray()
        try:
            while part := await upload.read(min(65536, limit + 1 - len(content))):
                content.extend(part)
                if len(content) > limit:
                    raise AppError("UPLOAD_TOO_LARGE", "Document exceeds upload size limit.", 413)
        finally:
            await upload.close()
        # Never use a client filename as a filesystem path or send it to a provider.
        extension = (upload.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
        with stage("extraction"):
            text = await run_in_threadpool(
                self.extraction.extract, bytes(content), extension, upload.content_type or ""
            )
        document_id = "DOC_" + uuid4().hex
        safe_filename = document_id + "." + extension.rsplit(".", 1)[-1].lower()
        row = {
            "_id": document_id,
            "patient_id": patient_id,
            "original_filename": safe_filename,
            "document_type": classify_document(text, document_type),
            "document_date": document_date.isoformat() if document_date else None,
            "processing_status": "processing",
            "chunk_count": 0,
            "created_at": datetime.now(timezone.utc),
        }
        await self.repository.create(patient_id, row)
        try:
            if self.privacy:
                with stage("privacy"):
                    text = await run_in_threadpool(self.privacy.sanitize, text)
            count = await self.ingestion.ingest(patient_id, row, text) if self.ingestion else 0
            row.update(processing_status="completed", chunk_count=count)
            updated = await self.repository.update(
                patient_id, document_id, {"processing_status": "completed", "chunk_count": count}
            )
            if not updated:
                raise AppError("DOCUMENT_NOT_FOUND", "Document was deleted during processing.", 404)
        except Exception:
            if self.ingestion and hasattr(self.ingestion, "remove"):
                await self.ingestion.remove(patient_id, document_id)
            await self.repository.update(patient_id, document_id, {"processing_status": "failed"})
            raise
        return public_document(row)

    async def list(self, patient_id: str) -> list[DocumentResponse]:
        return [public_document(row) for row in await self.repository.list(patient_id)]

    async def get(self, patient_id: str, document_id: str) -> DocumentResponse:
        row = await self.repository.get(patient_id, document_id)
        if row is None:
            raise AppError("DOCUMENT_NOT_FOUND", "Document was not found.", 404)
        return public_document(row)

    async def delete(self, patient_id: str, document_id: str) -> None:
        if not await self.repository.delete(patient_id, document_id):
            raise AppError("DOCUMENT_NOT_FOUND", "Document was not found.", 404)
