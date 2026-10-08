import logging
import mimetypes
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pymongo.errors import PyMongoError
from starlette.exceptions import HTTPException

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.frontend import WEB_ROOT
from app.api.frontend import router as frontend_router
from app.api.health import router as health_router
from app.config import Settings
from app.database.mongodb import MongoDatabase
from app.exceptions import AppError
from app.observability import RequestMiddleware, error_body


def create_app(settings: Settings | None = None, database_factory: Callable = MongoDatabase) -> FastAPI:
    # Windows registry MIME mappings may otherwise serve ES modules as plain text.
    mimetypes.add_type("text/javascript", ".mjs")
    mimetypes.add_type("text/javascript", ".js")
    mimetypes.add_type("text/css", ".css")
    mimetypes.add_type("image/svg+xml", ".svg")
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        database = database_factory(settings)
        application.state.database = database
        try:
            await database.ping()
            if hasattr(database, "ensure_indexes"):
                await database.ensure_indexes()
            if database_factory is MongoDatabase:
                from app.auth.security import signing_key

                signing_key(settings)
                logger = logging.getLogger("medical_rag")
                logger.setLevel(logging.INFO)
                if not logger.handlers:
                    handler = logging.StreamHandler()
                    handler.setFormatter(logging.Formatter("%(message)s"))
                    logger.addHandler(handler)
                from app.services.privacy import PresidioPrivacy

                application.state.privacy = PresidioPrivacy(
                    settings.presidio_nlp_model,
                    settings.pii_score_threshold,
                    settings.clinical_terms,
                    settings.clinical_terms_file,
                )
                from app.database.chunks import ChunkRepository
                from app.services.embeddings import create_embedding_service
                from app.services.ingestion import IngestionService

                application.state.embeddings = create_embedding_service(settings)
                application.state.ingestion = IngestionService(
                    application.state.privacy,
                    application.state.embeddings,
                    ChunkRepository(database),
                    settings,
                )
                from app.database.documents import DocumentRepository
                from app.services.retrieval import RetrievalService

                application.state.retrieval = RetrievalService(
                    ChunkRepository(database),
                    DocumentRepository(database),
                    application.state.embeddings,
                    settings,
                )
                from app.rag.graph import GraphRAGService
                from app.services.llm import StructuredLLMService

                application.state.llm = StructuredLLMService(settings)
                application.state.rag = GraphRAGService(
                    application.state.retrieval, application.state.llm, application.state.privacy, settings
                )
            yield
        finally:
            await database.close()

    application = FastAPI(title="Patient Medical RAG", lifespan=lifespan, debug=False)
    application.state.settings = settings
    application.add_middleware(
        RequestMiddleware, max_body_bytes=settings.max_upload_size_mb * 1024 * 1024 + 65536
    )
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(documents_router)
    application.include_router(chat_router)
    application.include_router(frontend_router)
    if (WEB_ROOT / "assets").is_dir():
        application.mount("/assets", StaticFiles(directory=WEB_ROOT / "assets"), name="frontend-assets")

    @application.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError):
        return JSONResponse(
            error_body(exc.code, exc.message, request.state.request_id), status_code=exc.status_code
        )

    @application.exception_handler(PyMongoError)
    async def database_error(request: Request, exc: PyMongoError):
        logging.getLogger("medical_rag").error("database_operation_failed")
        return JSONResponse(
            error_body("DATABASE_UNAVAILABLE", "Database is unavailable.", request.state.request_id),
            status_code=503,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            error_body("VALIDATION_ERROR", "Request validation failed.", request.state.request_id),
            status_code=422,
        )

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return JSONResponse(
            error_body("HTTP_ERROR", "Request could not be processed.", request.state.request_id),
            status_code=exc.status_code,
            headers=exc.headers,
        )

    return application


app = create_app()
