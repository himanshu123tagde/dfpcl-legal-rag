from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import Settings
from app.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HyDE prompt – tailored for the legal domain
# ---------------------------------------------------------------------------
_HYDE_SYSTEM_PROMPT = (
    "Act as a Senior Legal Researcher. "
    "Write a brief, 3-sentence technical passage that would likely appear "
    "in a legal document or judicial ruling answering the following question. "
    "Use formal legal terminology. "
    "DO NOT include specific names, dates, or case citations. "
    "Just focus on the legal principles."
)


@dataclass
class HydeService:
    """
    Generates a Hypothetical Document Embedding (HyDE) passage for a user
    query, then returns the embedding of that passage.

    Uses a lightweight *Mini* model (e.g. GPT-4o-mini) when configured;
    falls back to the primary GPT deployment otherwise.
    """

    openai: OpenAIService
    settings: Settings

    @property
    def _deployment(self) -> str | None:
        """Return the Mini deployment name, or None to use the primary GPT deployment."""
        val = self.settings.azure_openai_deployment_mini
        return val if val else None  # treats both None and "" as "not configured"

    def generate_hypothetical_passage(self, query_text: str) -> str:
        """
        Ask the LLM (Mini preferred) to write a short hypothetical legal
        passage that *would* answer ``query_text``.
        """
        passage = self.openai.generate_answer(
            system_prompt=_HYDE_SYSTEM_PROMPT,
            user_prompt=query_text,
            deployment_name=self._deployment,
            temperature=0.3,
            max_tokens=250,
        )
        logger.debug("HyDE passage generated (%d chars): %.120s…", len(passage), passage)
        return passage

    def generate_hyde_vector(self, query_text: str) -> list[float]:
        """
        End-to-end HyDE: generate hypothetical passage → embed it.
        """
        passage = self.generate_hypothetical_passage(query_text)
        return self.openai.embed_text(passage)
