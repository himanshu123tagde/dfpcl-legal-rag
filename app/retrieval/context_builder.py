from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.models.queries import Citation


def _compact_text(value: str) -> str:
    return " ".join(value.split())


def _build_summaries_block(
    docs: Sequence[Mapping[str, object]] | None,
    *,
    max_chars: int,
) -> str:
    if not docs or max_chars <= 0:
        return ""

    lines: list[str] = ["[Document summaries]"]
    remaining = max_chars - len(lines[0]) - 1

    for d in docs:
        doc_id = str(d.get("doc_id") or "")
        title = _compact_text(str(d.get("title") or "")).strip()
        doc_type = str(d.get("doc_type") or "")
        summary = _compact_text(str(d.get("full_summary") or "")).strip()

        if not summary:
            continue

        entry = f"- doc_id={doc_id or 'unknown'} title={title or 'unknown'} doc_type={doc_type or 'unknown'} summary={summary}"
        if len(entry) + 1 > remaining:
            break
        lines.append(entry)
        remaining -= len(entry) + 1

    if len(lines) == 1:
        return ""
    return "\n".join(lines)

def build_context_and_citations(
    chunks: Sequence[Mapping[str, object]],
    *,
    max_chunks: int,
    max_context_chars: int = 8000,
    doc_titles: Mapping[str, str] | None = None,
    doc_summaries: Sequence[Mapping[str, object]] | None = None,
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

    summaries_block = _build_summaries_block(doc_summaries, max_chars=min(2000, remaining_chars))
    if summaries_block:
        context_parts.append(summaries_block)
        remaining_chars -= len(summaries_block) + 2

    for idx, chunk in enumerate(selected, start=1):
        content = _compact_text(str(chunk.get("content") or "")).strip()
        if not content:
            continue

        doc_id = str(chunk.get("doc_id") or "")
        page_number = chunk.get("page_number")
        chunk_index = chunk.get("chunk_index")
        title = (doc_titles or {}).get(doc_id)

        block = (
            f"[Source {idx}]\n"
            f"doc_id: {doc_id or 'unknown'}\n"
            f"title: {title or 'unknown'}\n"
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
                title=title,
                page_number=page_number if isinstance(page_number, int) else None,
                chunk_index=chunk_index if isinstance(chunk_index, int) else None,
            )
        )

        if remaining_chars <= 0:
            break

    return "\n\n".join(context_parts), citations
