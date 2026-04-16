from __future__ import annotations

from dataclasses import dataclass

from app.models.documents import DocumentMetadata
from app.models.users import UserClaims
from app.repositories.cosmos_documents_repo import CosmosDocumentsRepository
from app.retrieval.query_analysis import QueryAnalysis


@dataclass(frozen=True)
class Stage1Result:
    candidates: list[DocumentMetadata]

    @property
    def candidate_doc_ids(self) -> list[str]:
        return [d.doc_id for d in self.candidates]

    @property
    def doc_titles(self) -> dict[str, str]:
        return {d.doc_id: d.title for d in self.candidates}


def run_stage1_metadata(
    *,
    cosmos_repo: CosmosDocumentsRepository,
    user: UserClaims,
    analysis: QueryAnalysis,
    limit: int = 25,
) -> Stage1Result:
    """
    Phase 6 Stage 1:
    - metadata + RBAC + classification filtering in Cosmos
    - returns candidate documents (with summaries when available)
    """
    docs = cosmos_repo.search_stage1(
        user=user,
        keyword=analysis.keyword,
        doc_type=analysis.doc_type,
        jurisdiction=analysis.jurisdiction,
        limit=limit,
    )
    # Retrieval should prefer only documents that are actually indexed.
    filtered = [d for d in docs if d.status == "completed" and (d.chunk_count or 0) > 0]
    return Stage1Result(candidates=filtered)
