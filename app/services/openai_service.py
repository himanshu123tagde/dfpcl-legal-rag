from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openai import AzureOpenAI

from app.config import Settings


@dataclass
class OpenAIService:
    settings: Settings

    def __post_init__(self) -> None:
        s = self.settings
        if not s.azure_openai_endpoint or not s.azure_openai_key:
            raise RuntimeError("Azure OpenAI is not configured (endpoint/key missing).")
        if not s.azure_openai_deployment_gpt:
            raise RuntimeError("Azure OpenAI GPT deployment name is missing.")
        if not s.azure_openai_deployment_embed:
            raise RuntimeError("Azure OpenAI embedding deployment name is missing.")

        self.client = AzureOpenAI(
            azure_endpoint=s.azure_openai_endpoint,
            api_key=s.azure_openai_key,
            api_version=s.azure_openai_api_version,
        )

    def embed_text(self, text: str) -> list[float]:
        """
        Returns embedding vector. For text-embedding-3-large this should be 3072 dims.
        """
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Batch embedding helper used by ingestion to reduce per-chunk round trips.
        """
        if not texts:
            return []
        resp = self.client.embeddings.create(
            model=self.settings.azure_openai_deployment_embed,
            input=texts,
        )
        return [item.embedding for item in resp.data]

    def generate_answer(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        deployment_name: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 700,
    ) -> str:
        """
        Generate a chat completion.

        ``deployment_name`` defaults to the primary GPT deployment but can be
        overridden (e.g. to target a cheaper Mini model for HyDE generation).
        """
        model = deployment_name or self.settings.azure_openai_deployment_gpt
        resp = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()