from pymongo.errors import DuplicateKeyError

from app.exceptions import AppError


class PatientRepository:
    def __init__(self, database):
        self.collection = database.db.patients

    async def create(self, patient: dict) -> None:
        try:
            await self.collection.insert_one(patient)
        except DuplicateKeyError as exc:
            raise AppError("EMAIL_EXISTS", "Email is already registered.", 409) from exc

    async def by_email(self, email: str) -> dict | None:
        return await self.collection.find_one({"email": email})

    async def by_id(self, patient_id: str) -> dict | None:
        return await self.collection.find_one({"_id": patient_id, "is_active": True})
