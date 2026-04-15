from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.models.queries import Citation


def _compact_text(value: str) -> str:
    return " ".join(value.split())


def build_context_and_citations(
    chunks: Sequence[Mapping[str, object]],
    *,
    max_chunks: int,
    max_context_chars: int = 8000,
) -> tuple[str, list[Citation]]:
    """
    Convert search hits into a prompt-ready context block and API citations.

    The output format is intentionally simple so Phase 6 can reuse this module
    even after Stage 1 summaries are introduced.
    """

    selected = list(chunks[:max_chunks])
    context_parts: list[str] = []
    citations: list[Citation] = []
    remaining_chars = max_context_chars

    for idx, chunk in enumerate(selected, start=1):
        content = _compact_text(str(chunk.get("content") or "")).strip()
        if not content:
            continue

        doc_id = str(chunk.get("doc_id") or "")
        page_number = chunk.get("page_number")
        chunk_index = chunk.get("chunk_index")

        block = (
            f"[Source {idx}]\n"
            f"doc_id: {doc_id or 'unknown'}\n"
            f"page_number: {page_number if page_number is not None else 'unknown'}\n"
            f"chunk_index: {chunk_index if chunk_index is not None else 'unknown'}\n"
            f"content: {content}"
        )

        if len(block) > remaining_chars and context_parts:
            break

        context_parts.append(block[:remaining_chars])
        remaining_chars -= len(block)

        citations.append(
            Citation(
                doc_id=doc_id or "unknown",
                page_number=page_number if isinstance(page_number, int) else None,
                chunk_index=chunk_index if isinstance(chunk_index, int) else None,
            )
        )

        if remaining_chars <= 0:
            break

    return "\n\n".join(context_parts), citations
