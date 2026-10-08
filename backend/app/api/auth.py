from fastapi import APIRouter, Depends

from app.dependencies import current_patient, patient_service
from app.schemas.auth import (
    LoginRequest,
    PatientResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.services.patients import PatientService

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(data: RegisterRequest, service: PatientService = Depends(patient_service)):
    return RegisterResponse(patient_id=await service.register(data))


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, service: PatientService = Depends(patient_service)):
    return await service.login(data)


@router.get("/me", response_model=PatientResponse)
async def me(patient: dict = Depends(current_patient)):
    return PatientResponse(patient_id=patient["_id"], name=patient["name"], email=patient["email"])
