from datetime import datetime, timezone
from uuid import uuid4

from starlette.concurrency import run_in_threadpool

from app.auth.security import hash_password, issue_token, verify_password
from app.exceptions import AppError
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


class PatientService:
    def __init__(self, repository, settings):
        self.repository = repository
        self.settings = settings

    async def register(self, data: RegisterRequest) -> str:
        patient_id = "PAT_" + uuid4().hex
        await self.repository.create(
            {
                "_id": patient_id,
                "name": data.name.strip(),
                "email": str(data.email).lower(),
                "password_hash": await run_in_threadpool(hash_password, data.password.get_secret_value()),
                "role": "patient",
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
            }
        )
        return patient_id

    async def login(self, data: LoginRequest) -> TokenResponse:
        patient = await self.repository.by_email(str(data.email).lower())
        # Hash a dummy password to avoid a cheap fast path for unknown accounts.
        encoded = (
            patient["password_hash"] if patient else await run_in_threadpool(hash_password, "dummy-password")
        )
        valid = await run_in_threadpool(verify_password, data.password.get_secret_value(), encoded)
        if not patient or not valid or not patient["is_active"] or patient["role"] != "patient":
            raise AppError("INVALID_CREDENTIALS", "Email or password is invalid.", 401)
        return TokenResponse(
            access_token=issue_token(patient["_id"], self.settings),
            expires_in=self.settings.access_token_expire_minutes * 60,
        )
