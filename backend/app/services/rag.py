import asyncio

from starlette.concurrency import run_in_threadpool

from app.exceptions import AppError
from app.rag.prompts import FALLBACK
from app.schemas.chat import ChatResponse, Source
from app.schemas.rag import GenerationResult


def format_context(rows: list[dict], max_chars: int) -> list[dict]:
    context = []
    used = 0
    for row in rows:
        text = row["text"][: max_chars - used]
        if not text:
            break
        context.append(
            {
                "document_id": row["document_id"],
                "document_type": row["document_type"],
                "document_date": row["document_date"],
                "source": row["source"],
                "text": text,
            }
        )
        used += len(text)
    return context


def response_from_result(result: GenerationResult, context: list[dict], request_id: str) -> ChatResponse:
    by_id = {r["document_id"]: r for r in context}
    if result.answer == FALLBACK or not result.source_ids or any(i not in by_id for i in result.source_ids):
        return ChatResponse(answer=FALLBACK, status="insufficient_context", sources=[], request_id=request_id)
    return ChatResponse(
        answer=result.answer,
        status="answered",
        sources=[
            Source(
                document_id=i,
                document_type=by_id[i]["document_type"],
                document_date=by_id[i]["document_date"],
            )
            for i in dict.fromkeys(result.source_ids)
        ],
        request_id=request_id,
    )


class BasicRAGService:
    def __init__(self, retrieval, llm, privacy, settings):
        self.retrieval = retrieval
        self.llm = llm
        self.privacy = privacy
        self.settings = settings

    async def query(self, patient_id: str, question: str, document_type, request_id: str) -> ChatResponse:
        sanitized = await run_in_threadpool(self.privacy.sanitize, question)
        rows = await self.retrieval.retrieve(patient_id, sanitized, document_type)
        context = format_context(rows, self.settings.max_context_chars)
        if not context:
            return ChatResponse(
                answer=FALLBACK, status="insufficient_context", sources=[], request_id=request_id
            )
        try:
            result = GenerationResult.model_validate(
                await asyncio.wait_for(
                    self.llm.generate(sanitized, context), self.settings.llm_timeout_seconds
                )
            )
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                "LLM_UNAVAILABLE", "Language model is unavailable or returned invalid output.", 503
            ) from exc
        return response_from_result(result, context, request_id)
