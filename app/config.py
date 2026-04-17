from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Phase 0:
    - Keep all Azure settings optional so the app runs without cloud dependencies.
    - Later phases will require specific values.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: str = "dev"
    log_level: str = "INFO"

    # API behavior
    api_title: str = "Legal RAG POC"
    api_version: str = "0.1.0"

    # Azure OpenAI (used from Phase 1)
    azure_openai_endpoint: str | None = None
    azure_openai_key: str | None = None
    azure_openai_api_version: str = "2024-02-15-preview"
    azure_openai_deployment_gpt: str | None = None
    azure_openai_deployment_embed: str | None = None
    azure_openai_deployment_mini: str | None = None

    # Cosmos DB (used from Phase 2)
    cosmos_endpoint: str | None = None
    cosmos_key: str | None = None
    cosmos_db_name: str = "legal-rag"
    cosmos_container_documents: str = "documents"

    # Azure AI Search (used from Phase 3)
    ai_search_endpoint: str | None = None
    ai_search_key: str | None = None
    ai_search_index_chunks: str = "legal-chunks"

    # Blob Storage (used from Phase 5)
    blob_connection_string: str | None = None
    blob_container_name: str = "legal-docs"

    # Service Bus (used from Phase 5)
    service_bus_connection_string: str | None = None
    service_bus_queue_ingestion: str = "ingestion-queue"

    # Redis (later)
    redis_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()