from app.database.documents import require_patient
from app.exceptions import AppError
from app.schemas.chunks import Chunk


class ChunkRepository:
    def __init__(self, database):
        self.collection = database.db.medical_chunks

    async def insert(self, patient_id: str, chunks: list[Chunk]) -> None:
        require_patient(patient_id)
        if any(c.patient_id != patient_id for c in chunks):
            raise AppError("OWNERSHIP_MISMATCH", "Chunk ownership is invalid.", 403)
        if chunks:
            await self.collection.insert_many([c.mongo_record() for c in chunks])

    async def delete_document(self, patient_id: str, document_id: str) -> None:
        require_patient(patient_id)
        await self.collection.delete_many({"patient_id": patient_id, "document_id": document_id})

    async def summary_rows(self, patient_id: str, document_type=None) -> list[dict]:
        require_patient(patient_id)
        filters = {"patient_id": patient_id}
        if document_type is not None:
            filters["document_type"] = document_type
        # Fetch one extra row to detect the bound rather than silently omit records.
        return (
            await self.collection.find(filters, {"embedding": 0})
            .sort([("document_date", 1), ("document_id", 1), ("chunk_index", 1)])
            .to_list(1001)
        )

    async def search(self, patient_id: str, vector: list[float], settings, document_type=None) -> list[dict]:
        require_patient(patient_id)
        filters = {"patient_id": {"$eq": patient_id}}
        if document_type is not None:
            filters["document_type"] = {"$eq": document_type}
        pipeline = [
            {
                "$vectorSearch": {
                    "index": settings.vector_index_name,
                    "path": "embedding",
                    "queryVector": vector,
                    "numCandidates": settings.rag_fetch_k,
                    "limit": settings.rag_top_k,
                    "filter": filters,
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "patient_id": 1,
                    "document_id": 1,
                    "document_type": 1,
                    "document_date": 1,
                    "source": 1,
                    "chunk_index": 1,
                    "text": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]
        cursor = await self.collection.aggregate(pipeline)
        return await cursor.to_list(settings.rag_top_k)
