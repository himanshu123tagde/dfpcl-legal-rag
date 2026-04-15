from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from app.config import Settings
from app.models.chunks import Chunk
from app.utils.azure_clients import get_search_client

# Query model import differs across SDK versions; handle gracefully.
try:
    # Newer SDK pattern
    from azure.search.documents.models import VectorizedQuery  # type: ignore
except Exception:  # pragma: no cover
    VectorizedQuery = None  # type: ignore


@dataclass
class SearchChunksRepository:
    settings: Settings

    @property
    def index_name(self) -> str:
        return self.settings.ai_search_index_chunks

    def upload_chunks(self, chunks: Sequence[Chunk]) -> None:
        """
        Push chunks to AI Search.
        In production: batch and add retry/backoff for 429/503.
        """
        client = get_search_client(self.settings, self.index_name)

        docs = []
        for c in chunks:
            d = c.model_dump()
            # AI Search will reject None for vector field in some configurations.
            # Keep None out if not embedded yet.
            if d.get("content_vector") is None:
                d.pop("content_vector", None)
            docs.append(d)

        if not docs:
            return

        result = client.upload_documents(documents=docs)
        failed = [r for r in result if not r.succeeded]
        if failed:
            raise RuntimeError(f"AI Search upload failed for {len(failed)} documents: {failed[:3]}")

    def hybrid_search_scoped(
        self,
        *,
        query_text: str,
        query_vector: List[float],
        candidate_doc_ids: Optional[Sequence[str]] = None,
        top: int = 10,
        k_nearest: int = 50,
        language: Optional[str] = None,
    ) -> list[dict]:
        """
        Executes a hybrid search (BM25 + vector) scoped to candidate doc_ids.
        - Scoping uses search.in(doc_id, 'a,b,c', ',') which scales better than huge OR chains.
        """
        client = get_search_client(self.settings, self.index_name)

        filter_parts: list[str] = []

        if candidate_doc_ids:
            # doc_id values are UUIDs in our design, safe to join by comma
            csv = ",".join(candidate_doc_ids)
            filter_parts.append(f"search.in(doc_id, '{csv}', ',')")

        if language:
            filter_parts.append(f"language eq '{language}'")

        odata_filter = " and ".join(filter_parts) if filter_parts else None

        # Prefer vector_queries API (newer SDK). If unavailable, raise with clear message.
        if VectorizedQuery is None:
            raise RuntimeError(
                "Your azure-search-documents SDK is missing VectorizedQuery. "
                "Upgrade azure-search-documents to a newer version."
            )

        vq = VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=k_nearest,
            fields="content_vector",
        )

        results = client.search(
            search_text=query_text,
            vector_queries=[vq],
            filter=odata_filter,
            top=top,
            select=["chunk_id", "doc_id", "content", "keywords", "page_number", "chunk_index", "language"],
        )

        # Convert SearchItemPaged -> list[dict]
        out: list[dict] = []
        for r in results:
            out.append(dict(r))
        return out