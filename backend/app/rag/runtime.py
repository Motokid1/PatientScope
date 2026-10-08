import asyncio

from app.exceptions import AppError


class RAGServices:
    def __init__(self, retrieval, llm, privacy, settings):
        self.retrieval = retrieval
        self.llm = llm
        self.privacy = privacy
        self.settings = settings

    async def call(self, schema, method, *args, **kwargs):
        try:
            result = await asyncio.wait_for(method(*args, **kwargs), self.settings.llm_timeout_seconds)
            return schema.model_validate(result)
        except AppError:
            raise
        except asyncio.TimeoutError as exc:
            raise AppError("LLM_TIMEOUT", "The language model request timed out.", 503) from exc
        except Exception as exc:
            raise AppError(
                "LLM_UNAVAILABLE", "Language model is unavailable or returned invalid output.", 503
            ) from exc
