from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    app_env: Literal["development", "test", "production"] = "development"
    mongodb_uri: SecretStr = SecretStr("mongodb://localhost:27017")
    mongodb_db_name: str = Field(default="medical_rag", min_length=1, max_length=64)
    mongodb_timeout_ms: int = Field(default=5000, ge=100, le=60000)
    jwt_secret: SecretStr = SecretStr("")
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=60, ge=1, le=1440)
    max_upload_size_mb: int = Field(default=15, ge=1, le=100)
    max_extracted_chars: int = Field(default=2_000_000, ge=1000, le=10_000_000)
    presidio_nlp_model: str = "en_core_web_sm"
    pii_score_threshold: float = Field(default=0.4, ge=0, le=1)
    clinical_terms: list[str] = Field(default_factory=list)
    clinical_terms_file: str | None = None
    chunk_size: int = Field(default=800, ge=100, le=8000)
    chunk_overlap: int = Field(default=120, ge=0, le=4000)
    embedding_provider: Literal["huggingface", "openai"] = "huggingface"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimensions: int = Field(default=384, ge=1, le=4096)
    embedding_device: str = "cpu"
    embedding_cache_dir: str = "models/embeddings"
    embedding_local_files_only: bool = True
    huggingface_token: SecretStr = SecretStr("")
    embedding_api_key: SecretStr = SecretStr("")
    embedding_timeout_seconds: float = Field(default=30, gt=0, le=120)
    embedding_batch_size: int = Field(default=32, ge=1, le=256)
    vector_index_name: str = "medical_chunks_vector"
    rag_top_k: int = Field(default=5, ge=1, le=30)
    rag_fetch_k: int = Field(default=15, ge=1, le=10000)
    llm_provider: Literal["groq", "openai"] = "groq"
    llm_model: str = "openai/gpt-oss-20b"
    groq_api_key: SecretStr = SecretStr("")
    llm_api_key: SecretStr = SecretStr("")
    llm_timeout_seconds: float = Field(default=30, gt=0, le=120)
    max_context_chars: int = Field(default=24000, ge=1000, le=100000)
    relevance_threshold: float = Field(default=0.72, ge=0, le=1)
    llm_relevance_enabled: bool = True
    max_query_retries: int = Field(default=2, ge=0, le=5)
    max_generation_retries: int = Field(default=1, ge=0, le=3)
    rag_timeout_seconds: float = Field(default=180, gt=0, le=600)

    @model_validator(mode="after")
    def valid_chunking(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be smaller than chunk size")
        if self.rag_fetch_k < self.rag_top_k:
            raise ValueError("Candidate count must be at least Top-K")
        return self

    @field_validator("mongodb_uri")
    @classmethod
    def mongo_scheme(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError("Expected a MongoDB URI")
        return value

    @field_validator("mongodb_db_name")
    @classmethod
    def database_name(cls, value: str) -> str:
        if any(c in value for c in '/\\. "$*<>:|?'):
            raise ValueError("Invalid MongoDB database name")
        return value
