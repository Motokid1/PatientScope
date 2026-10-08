from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.security import decode_token
from app.database.documents import DocumentRepository
from app.database.patients import PatientRepository
from app.exceptions import AppError
from app.observability import stage
from app.services.documents import DocumentService
from app.services.patients import PatientService

bearer = HTTPBearer(auto_error=False)


def document_repository(request: Request):
    override = getattr(request.app.state, "document_repository", None)
    return override if override is not None else DocumentRepository(request.app.state.database)


def document_service(request: Request, repository=Depends(document_repository)) -> DocumentService:
    return DocumentService(
        repository,
        request.app.state.settings,
        getattr(request.app.state, "ingestion", None),
        getattr(request.app.state, "privacy", None),
    )


def patient_repository(request: Request):
    override = getattr(request.app.state, "patient_repository", None)
    return override if override is not None else PatientRepository(request.app.state.database)


def patient_service(request: Request, repository=Depends(patient_repository)) -> PatientService:
    return PatientService(repository, request.app.state.settings)


async def current_patient(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    repository=Depends(patient_repository),
) -> dict:
    if credentials is None:
        raise AppError("INVALID_TOKEN", "Authentication token is required.", 401)
    with stage("authentication"):
        patient_id = decode_token(credentials.credentials, request.app.state.settings)
        patient = await repository.by_id(patient_id)
    if not patient or patient["role"] != "patient":
        raise AppError("INVALID_TOKEN", "Authentication token is invalid.", 401)
    return patient
