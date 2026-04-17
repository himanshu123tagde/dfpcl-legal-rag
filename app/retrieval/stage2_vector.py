from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from app.repositories.search_chunks_repo import SearchChunksRepository
from app.retrieval.query_analysis import QueryAnalysis
from app.services.hyde_service import HydeService
from app.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Stage2Result:
    chunks: list[dict[str, Any]]
    used_scoped_search: bool
    used_hyde: bool = False


def run_stage2_scoped_hybrid(
    *,
    search_repo: SearchChunksRepository,
    openai: OpenAIService,
    analysis: QueryAnalysis,
    candidate_doc_ids: Optional[list[str]],
    top_k: int,
    hyde_service: HydeService | None = None,
) -> Stage2Result:
    """
    Anchored Hybrid Retrieval (Phase 7 – HyDE):
    - If ``analysis.needs_hyde`` and a ``hyde_service`` is available, the
      **vector** component uses the embedding of a hypothetical legal
      passage while the **BM25** component keeps the original query text.
      This "anchors" the lexical match to the real question while letting
      the vector search reach semantically richer territory.
    - Otherwise falls back to the standard behaviour (embed the raw query).
    - Scoped to candidate_doc_ids when Stage 1 returned any.
    - Falls back to unscoped if scoped yields zero results.
    """
    query_text = analysis.optimized_query_text
    used_hyde = False

    # --- Decide which vector to use ---
    if analysis.needs_hyde and hyde_service is not None:
        logger.info("HyDE triggered for query: %.100s", query_text)
        query_vector = hyde_service.generate_hyde_vector(query_text)
        used_hyde = True
    else:
        query_vector = openai.embed_text(query_text)

    # --- Scoped / unscoped search ---
    scoped_doc_ids = [d for d in (candidate_doc_ids or []) if d]
    used_scoped = bool(scoped_doc_ids)

    hits = search_repo.hybrid_search_scoped(
        query_text=query_text,          # BM25 always uses original text
        query_vector=query_vector,      # vector may be HyDE-derived
        candidate_doc_ids=scoped_doc_ids or None,
        top=top_k,
        k_nearest=max(top_k * 5, 50),
        language=analysis.language,
    )

    if hits or not scoped_doc_ids:
        return Stage2Result(chunks=hits, used_scoped_search=used_scoped, used_hyde=used_hyde)

    # Scoped search found nothing; try again unscoped as a safe fallback.
    hits2 = search_repo.hybrid_search_scoped(
        query_text=query_text,
        query_vector=query_vector,
        candidate_doc_ids=None,
        top=top_k,
        k_nearest=max(top_k * 5, 50),
        language=analysis.language,
    )
    return Stage2Result(chunks=hits2, used_scoped_search=False, used_hyde=used_hyde)
