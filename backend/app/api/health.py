from fastapi import APIRouter, Request

from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="healthy")


@router.get("/ready", response_model=HealthResponse)
async def ready(request: Request) -> HealthResponse:
    await request.app.state.database.ping()
    return HealthResponse(status="ready")
