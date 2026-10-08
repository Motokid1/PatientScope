import asyncio
import math
import threading
from typing import Protocol

from app.exceptions import AppError


class EmbeddingService(Protocol):
    async def embed_text(self, text: str) -> list[float]: ...
    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


def validate_vectors(vectors: list[list[float]], count: int, dimensions: int) -> None:
    if len(vectors) != count or any(
        len(v) != dimensions or not all(math.isfinite(x) for x in v) or not any(v) for v in vectors
    ):
        raise AppError("INVALID_EMBEDDINGS", "Embedding provider returned invalid vectors.", 503)


class OpenAIEmbeddingService:
    def __init__(self, settings):
        self.settings = settings
        self._client = None

    def client(self):
        if self._client is None:
            from langchain_openai import OpenAIEmbeddings

            key = self.settings.embedding_api_key.get_secret_value()
            if not key:
                raise AppError("EMBEDDING_CONFIGURATION", "Embedding service is not configured.", 503)
            self._client = OpenAIEmbeddings(
                model=self.settings.embedding_model,
                dimensions=self.settings.embedding_dimensions,
                api_key=key,
                request_timeout=self.settings.embedding_timeout_seconds,
                max_retries=0,
            )
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        return (await self.embed_documents([text]))[0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            vectors = await asyncio.wait_for(
                self.client().aembed_documents(texts), timeout=self.settings.embedding_timeout_seconds
            )
            validate_vectors(vectors, len(texts), self.settings.embedding_dimensions)
            return vectors
        except AppError:
            raise
        except Exception as exc:
            raise AppError("EMBEDDING_UNAVAILABLE", "Embedding service is unavailable.", 503) from exc


class HuggingFaceEmbeddingService:
    """Local sentence-transformer inference; no clinical text leaves this process."""

    def __init__(self, settings):
        self.settings = settings
        self._client = None
        self._lock = threading.RLock()

    def client(self):
        with self._lock:
            if self._client is None:
                try:
                    from sentence_transformers import SentenceTransformer

                    model = SentenceTransformer(
                        self.settings.embedding_model,
                        device=self.settings.embedding_device,
                        cache_folder=self.settings.embedding_cache_dir,
                        local_files_only=self.settings.embedding_local_files_only,
                        trust_remote_code=False,
                        token=self.settings.huggingface_token.get_secret_value() or None,
                    )
                    dimension = (
                        getattr(model, "get_embedding_dimension", None)
                        or getattr(model, "get_sentence_embedding_dimension")
                    )()
                    if dimension != self.settings.embedding_dimensions:
                        raise AppError(
                            "EMBEDDING_CONFIGURATION",
                            "Embedding model dimensions do not match configuration.",
                            503,
                        )
                    self._client = model
                except AppError:
                    raise
                except Exception as exc:
                    raise AppError(
                        "EMBEDDING_CONFIGURATION",
                        "Local embedding model is unavailable. Install the Hugging Face extra and download the configured model.",
                        503,
                    ) from exc
            return self._client

    def _encode(self, texts):
        with self._lock:
            return (
                self.client()
                .encode(
                    texts,
                    batch_size=self.settings.embedding_batch_size,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
                .tolist()
            )

    async def embed_text(self, text: str) -> list[float]:
        return (await self.embed_documents([text]))[0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            vectors = await asyncio.wait_for(
                asyncio.to_thread(self._encode, texts), self.settings.embedding_timeout_seconds
            )
            validate_vectors(vectors, len(texts), self.settings.embedding_dimensions)
            return vectors
        except AppError:
            raise
        except Exception as exc:
            raise AppError("EMBEDDING_UNAVAILABLE", "Local embedding service is unavailable.", 503) from exc


def create_embedding_service(settings) -> EmbeddingService:
    if settings.embedding_provider == "huggingface":
        return HuggingFaceEmbeddingService(settings)
    return OpenAIEmbeddingService(settings)
