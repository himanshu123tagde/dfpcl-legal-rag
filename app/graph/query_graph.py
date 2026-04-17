from __future__ import annotations

import logging

from app.generation.prompts import LEGAL_RAG_SYSTEM_PROMPT, build_grounded_user_prompt
from app.models.queries import QueryRequest, QueryResponse
from app.models.users import UserClaims
from app.repositories.cosmos_documents_repo import CosmosDocumentsRepository
from app.repositories.search_chunks_repo import SearchChunksRepository
from app.retrieval.context_builder import build_context_and_citations
from app.retrieval.query_analysis import analyze_query
from app.retrieval.stage1_metadata import run_stage1_metadata
from app.retrieval.stage2_vector import run_stage2_scoped_hybrid
from app.services.hyde_service import HydeService
from app.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

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


def execute_query_phase6(
    *,
    openai: OpenAIService,
    search_repo: SearchChunksRepository,
    cosmos_repo: CosmosDocumentsRepository,
    user: UserClaims,
    req: QueryRequest,
    hyde_service: HydeService | None = None,
) -> QueryResponse:
    """
    Phase 6 + HyDE (Anchored Hybrid Retrieval):
    - Analyze query: extract keyword/filters + decide if HyDE is needed
    - Stage 1: Cosmos metadata + RBAC/classification -> candidate docs (and summaries)
    - Stage 2: AI Search hybrid search scoped to candidate doc_ids
      - If needs_hyde=True: vector = HyDE passage embedding; BM25 = original text
      - If needs_hyde=False: vector = raw query embedding
    - Build context from chunks + summaries
    - Generate grounded answer
    """
    analysis = analyze_query(req.question)
    logger.info(
        "Query analysis: needs_hyde=%s doc_type=%s keyword=%s",
        analysis.needs_hyde,
        analysis.doc_type,
        analysis.keyword,
    )

    stage1 = run_stage1_metadata(cosmos_repo=cosmos_repo, user=user, analysis=analysis, limit=25)
    stage2 = run_stage2_scoped_hybrid(
        search_repo=search_repo,
        openai=openai,
        analysis=analysis,
        candidate_doc_ids=stage1.candidate_doc_ids,
        top_k=req.top_k,
        hyde_service=hyde_service,
    )

    logger.info("Stage2: used_hyde=%s used_scoped=%s chunks=%d", stage2.used_hyde, stage2.used_scoped_search, len(stage2.chunks))

    if not stage2.chunks:
        return QueryResponse(answer=_NO_CONTEXT_ANSWER)

    summaries_for_context = [d.model_dump() for d in stage1.candidates]
    context, citations = build_context_and_citations(
        stage2.chunks,
        max_chunks=req.top_k,
        doc_titles=stage1.doc_titles,
        doc_summaries=summaries_for_context,
    )
    if not context:
        return QueryResponse(answer=_NO_CONTEXT_ANSWER)

    user_prompt = build_grounded_user_prompt(question=req.question, context=context)
    answer = openai.generate_answer(system_prompt=LEGAL_RAG_SYSTEM_PROMPT, user_prompt=user_prompt)
    return QueryResponse(
        answer=answer,
        citations=citations,
        used_hyde=stage2.used_hyde,
        used_scoped_search=stage2.used_scoped_search,
    )