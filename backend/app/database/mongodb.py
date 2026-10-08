from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

from app.config import Settings
from app.exceptions import AppError


class MongoDatabase:
    def __init__(self, settings: Settings):
        try:
            self.client = AsyncMongoClient(
                settings.mongodb_uri.get_secret_value(),
                serverSelectionTimeoutMS=settings.mongodb_timeout_ms,
                connectTimeoutMS=settings.mongodb_timeout_ms,
                timeoutMS=settings.mongodb_timeout_ms,
            )
        except (PyMongoError, ValueError):
            raise AppError("DATABASE_CONFIGURATION", "Database configuration is invalid.", 503) from None
        self.db = self.client[settings.mongodb_db_name]

    async def ping(self) -> None:
        try:
            await self.client.admin.command("ping")
        except PyMongoError:
            raise AppError("DATABASE_UNAVAILABLE", "Database is unavailable.", 503) from None

    async def close(self) -> None:
        await self.client.close()

    async def ensure_indexes(self) -> None:
        await self.db.patients.create_index("email", unique=True)
        await self.db.documents.create_index("patient_id")
        await self.db.medical_chunks.create_index("patient_id")
        await self.db.medical_chunks.create_index("document_id")
        await self.db.medical_chunks.create_index("document_type")
