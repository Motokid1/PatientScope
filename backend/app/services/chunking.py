from datetime import datetime, timezone
from uuid import uuid4

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.database.documents import require_patient
from app.exceptions import AppError
from app.schemas.chunks import Chunk


class ChunkingService:
    def __init__(self, settings):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
        )

    def split(self, text: str) -> list[str]:
        return self.splitter.split_text(text)

    def records(
        self, patient_id: str, document: dict, texts: list[str], vectors: list[list[float]]
    ) -> list[Chunk]:
        require_patient(patient_id)
        if document["patient_id"] != patient_id:
            raise AppError("OWNERSHIP_MISMATCH", "Document ownership is invalid.", 403)
        if len(texts) != len(vectors):
            raise AppError("INVALID_EMBEDDINGS", "Embedding count does not match chunks.", 503)
        return [
            Chunk(
                chunk_id="CHUNK_" + uuid4().hex,
                document_id=document["_id"],
                patient_id=patient_id,
                document_type=document["document_type"],
                document_date=document["document_date"],
                source=document["original_filename"],
                chunk_index=index,
                text=text,
                embedding=vector,
                created_at=datetime.now(timezone.utc),
            )
            for index, (text, vector) in enumerate(zip(texts, vectors, strict=True))
        ]
