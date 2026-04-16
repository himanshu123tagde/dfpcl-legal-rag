from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from app.repositories.search_chunks_repo import SearchChunksRepository
from app.retrieval.query_analysis import QueryAnalysis
from app.services.openai_service import OpenAIService


@dataclass(frozen=True)
class Stage2Result:
    chunks: list[dict[str, Any]]
    used_scoped_search: bool


def run_stage2_scoped_hybrid(
    *,
    search_repo: SearchChunksRepository,
    openai: OpenAIService,
    analysis: QueryAnalysis,
    candidate_doc_ids: Optional[list[str]],
    top_k: int,
) -> Stage2Result:
    """
    Phase 6 Stage 2:
    - Hybrid vector+BM25 search in AI Search
    - Scoped to candidate_doc_ids when Stage 1 returned any
    - Falls back to unscoped if scoped yields zero results
    """
    query_text = analysis.optimized_query_text
    query_vector = openai.embed_text(query_text)

    scoped_doc_ids = [d for d in (candidate_doc_ids or []) if d]
    used_scoped = bool(scoped_doc_ids)

    hits = search_repo.hybrid_search_scoped(
        query_text=query_text,
        query_vector=query_vector,
        candidate_doc_ids=scoped_doc_ids or None,
        top=top_k,
        k_nearest=max(top_k * 5, 50),
        language=analysis.language,
    )

    if hits or not scoped_doc_ids:
        return Stage2Result(chunks=hits, used_scoped_search=used_scoped)

    # Scoped search found nothing; try again unscoped as a safe fallback.
    hits2 = search_repo.hybrid_search_scoped(
        query_text=query_text,
        query_vector=query_vector,
        candidate_doc_ids=None,
        top=top_k,
        k_nearest=max(top_k * 5, 50),
        language=analysis.language,
    )
    return Stage2Result(chunks=hits2, used_scoped_search=False)
