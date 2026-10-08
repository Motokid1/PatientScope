import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.exceptions import AppError

router = APIRouter(tags=["frontend"])
WEB_ROOT = Path(os.getenv("FRONTEND_DIST_DIR") or Path(__file__).resolve().parents[3] / "frontend" / "dist")


class UIConfig(BaseModel):
    max_upload_size_mb: int
    question_max_length: int = 2000
    query_timeout_seconds: float
    supported_extensions: list[str] = ["pdf", "txt", "docx"]


@router.get("/", include_in_schema=False)
async def portal() -> FileResponse:
    if not (WEB_ROOT / "index.html").is_file():
        raise AppError(
            "FRONTEND_NOT_BUILT",
            "Run npm install and npm run build in frontend/, or use the Vite development server.",
            503,
        )
    return FileResponse(
        WEB_ROOT / "index.html",
        media_type="text/html",
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
            "base-uri 'none'; form-action 'self'; object-src 'none'",
        },
    )


@router.get("/api/v1/ui/config", response_model=UIConfig)
async def ui_config(request: Request) -> UIConfig:
    settings = request.app.state.settings
    return UIConfig(
        max_upload_size_mb=settings.max_upload_size_mb, query_timeout_seconds=settings.rag_timeout_seconds
    )


@router.get("/favicon.svg", include_in_schema=False)
async def favicon() -> FileResponse:
    if not (WEB_ROOT / "favicon.svg").is_file():
        raise AppError("FRONTEND_NOT_BUILT", "Frontend assets are not built.", 404)
    return FileResponse(WEB_ROOT / "favicon.svg", media_type="image/svg+xml")
