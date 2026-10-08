from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import Settings
from app.exceptions import AppError


def hash_password(password: str) -> str:
    return PasswordHasher().hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return PasswordHasher().verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def signing_key(settings: Settings) -> str:
    key = settings.jwt_secret.get_secret_value()
    if len(key.encode()) < 32:
        raise AppError("AUTH_CONFIGURATION", "Authentication is unavailable.", 503)
    return key


def issue_token(patient_id: str, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": patient_id,
            "role": "patient",
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        },
        signing_key(settings),
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str, settings: Settings) -> str:
    try:
        payload = jwt.decode(
            token,
            signing_key(settings),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "role", "iat", "exp"]},
        )
        if (
            payload["role"] != "patient"
            or not isinstance(payload["sub"], str)
            or not payload["sub"].startswith("PAT_")
            or not isinstance(payload["iat"], (int, float))
            or not isinstance(payload["exp"], (int, float))
            or payload["exp"] <= payload["iat"]
        ):
            raise jwt.InvalidTokenError()
        return payload["sub"]
    except jwt.InvalidTokenError as exc:
        raise AppError("INVALID_TOKEN", "Authentication token is invalid.", 401) from exc
