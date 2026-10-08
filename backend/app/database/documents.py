from app.exceptions import AppError


def require_patient(patient_id: str) -> None:
    if not isinstance(patient_id, str) or not patient_id.startswith("PAT_"):
        raise AppError("INVALID_IDENTITY", "Authenticated identity is required.", 401)


class DocumentRepository:
    def __init__(self, database):
        self.collection = database.db.documents
        self.chunks = database.db.medical_chunks

    async def create(self, patient_id: str, document: dict) -> None:
        require_patient(patient_id)
        if document["patient_id"] != patient_id:
            raise AppError("OWNERSHIP_MISMATCH", "Document ownership is invalid.", 403)
        await self.collection.insert_one(document)

    async def list(self, patient_id: str) -> list[dict]:
        require_patient(patient_id)
        return await self.collection.find({"patient_id": patient_id}).sort("created_at", -1).to_list(1000)

    async def get(self, patient_id: str, document_id: str) -> dict | None:
        require_patient(patient_id)
        return await self.collection.find_one({"_id": document_id, "patient_id": patient_id})

    async def update(self, patient_id: str, document_id: str, fields: dict) -> bool:
        require_patient(patient_id)
        if set(fields) - {"processing_status", "chunk_count"}:
            raise ValueError("Only processing fields can be updated")
        result = await self.collection.update_one(
            {"_id": document_id, "patient_id": patient_id}, {"$set": fields}
        )
        return result.matched_count == 1

    async def delete(self, patient_id: str, document_id: str) -> bool:
        require_patient(patient_id)
        # Hide the metadata first; retrieval must recheck completed document ownership.
        row = await self.get(patient_id, document_id)
        if row is None:
            return False
        await self.update(patient_id, document_id, {"processing_status": "failed"})
        await self.chunks.delete_many({"document_id": document_id, "patient_id": patient_id})
        result = await self.collection.delete_one({"_id": document_id, "patient_id": patient_id})
        return result.deleted_count == 1
