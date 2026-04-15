from __future__ import annotations

from app.generation.prompts import LEGAL_RAG_SYSTEM_PROMPT, build_grounded_user_prompt
from app.models.queries import QueryRequest, QueryResponse
from app.repositories.search_chunks_repo import SearchChunksRepository
from app.retrieval.context_builder import build_context_and_citations
from app.services.openai_service import OpenAIService


_NO_CONTEXT_ANSWER = (
    "I could not find enough indexed legal context to answer this question yet. "
    "Please upload or index more relevant documents and try again."
)


def execute_query_phase4(
    *,
    openai: OpenAIService,
    search_repo: SearchChunksRepository,
    req: QueryRequest,
) -> QueryResponse:
    """
    Phase 4 vertical slice:
    - Embed the question
    - Retrieve top chunks from AI Search
    - Build prompt context + API citations
    - Ask the model to answer using only retrieved context
    """

    query_vector = openai.embed_text(req.question)

    search_hits = search_repo.hybrid_search_scoped(
        query_text=req.question,
        query_vector=query_vector,
        candidate_doc_ids=None,
        top=req.top_k,
        k_nearest=max(req.top_k * 5, 20),
    )

    if not search_hits:
        return QueryResponse(answer=_NO_CONTEXT_ANSWER)

    context, citations = build_context_and_citations(search_hits, max_chunks=req.top_k)
    if not context:
        return QueryResponse(answer=_NO_CONTEXT_ANSWER)

    user_prompt = build_grounded_user_prompt(question=req.question, context=context)
    answer = openai.generate_answer(
        system_prompt=LEGAL_RAG_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    return QueryResponse(answer=answer, citations=citations)