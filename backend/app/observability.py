import json
import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from uuid import uuid4

from starlette.types import ASGIApp, Receive, Scope, Send

from app.schemas.common import ErrorDetail, ErrorResponse


@dataclass
class Telemetry:
    request_id: str
    timings: dict[str, float] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)


_telemetry: ContextVar[Telemetry | None] = ContextVar("medical_rag_telemetry", default=None)


@contextmanager
def telemetry_scope(request_id: str):
    existing = _telemetry.get()
    token = None
    metrics = existing if existing and existing.request_id == request_id else Telemetry(request_id)
    if metrics is not existing:
        token = _telemetry.set(metrics)
    try:
        yield metrics
    finally:
        if token is not None:
            _telemetry.reset(token)


@contextmanager
def stage(name: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        metrics = _telemetry.get()
        if metrics is not None:
            metrics.timings[name + "_ms"] = (
                metrics.timings.get(name + "_ms", 0) + (time.perf_counter() - start) * 1000
            )
            metrics.counts[name + "_calls"] = metrics.counts.get(name + "_calls", 0) + 1


def error_body(code: str, message: str, request_id: str) -> dict:
    return ErrorResponse(error=ErrorDetail(code=code, message=message), request_id=request_id).model_dump()


class RequestMiddleware:
    """Emit only server-generated identifiers and numeric telemetry, never inputs."""

    def __init__(self, app: ASGIApp, max_body_bytes: int = 16 * 1024 * 1024):
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.logger = logging.getLogger("medical_rag.requests")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = "REQ_" + uuid4().hex
        metrics = Telemetry(request_id)
        metrics_token = _telemetry.set(metrics)
        scope.setdefault("state", {})["request_id"] = request_id
        start = time.perf_counter()
        status = 500
        started = False

        async def tracked_send(message: dict) -> None:
            nonlocal status, started
            if message["type"] == "http.response.start":
                started = True
                status = message["status"]
                message["headers"] = list(message.get("headers", [])) + [
                    (b"x-request-id", request_id.encode()),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"x-frame-options", b"DENY"),
                    (b"cache-control", b"no-store"),
                ]
            await send(message)

        try:
            # Bound the body before FastAPI/Starlette's multipart parser spools it.
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                body.extend(message.get("body", b""))
                if len(body) > self.max_body_bytes:
                    payload = json.dumps(
                        error_body("UPLOAD_TOO_LARGE", "Request exceeds size limit.", request_id)
                    ).encode()
                    await tracked_send(
                        {
                            "type": "http.response.start",
                            "status": 413,
                            "headers": [(b"content-type", b"application/json")],
                        }
                    )
                    await tracked_send({"type": "http.response.body", "body": payload})
                    return
                if not message.get("more_body", False):
                    break
            delivered = False

            async def bounded_receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            await self.app(scope, bounded_receive, tracked_send)
        except Exception:
            # Do not log exception text: drivers and parsers may include PHI/secrets.
            self.logger.error(json.dumps({"event": "request_failed", "request_id": request_id}))
            if started:
                raise
            body = json.dumps(
                error_body("INTERNAL_ERROR", "An internal error occurred.", request_id)
            ).encode()
            await tracked_send(
                {
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await tracked_send({"type": "http.response.body", "body": body})
        finally:
            self.logger.info(
                json.dumps(
                    {
                        "event": "request_complete",
                        "request_id": request_id,
                        "status": status,
                        "total_ms": round((time.perf_counter() - start) * 1000, 3),
                        **{k: round(v, 3) for k, v in metrics.timings.items()},
                        **metrics.counts,
                    }
                )
            )
            _telemetry.reset(metrics_token)
