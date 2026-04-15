from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from app.ingestion.extractors.pdf_extractor import ExtractedPage
from app.utils.text_utils import normalize_whitespace

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class ChunkDraft:
    content: str
    page_number: int | None
    chunk_index: int
    language: str = "en"
    keywords: list[str] | None = None


def _split_oversized_text(text: str, max_chars: int) -> list[str]:
    sentences = [normalize_whitespace(part) for part in _SENTENCE_SPLIT_RE.split(text) if part.strip()]
    if not sentences:
        return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]

    parts: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip()
        if current and len(candidate) > max_chars:
            parts.append(current)
            current = sentence
        else:
            current = candidate

    if current:
        parts.append(current)

    expanded: list[str] = []
    for part in parts:
        if len(part) <= max_chars:
            expanded.append(part)
        else:
            expanded.extend(part[i : i + max_chars] for i in range(0, len(part), max_chars))
    return expanded


def chunk_pdf_pages(
    pages: Iterable[ExtractedPage],
    *,
    language: str = "en",
    target_chars: int = 1200,
) -> list[ChunkDraft]:
    chunks: list[ChunkDraft] = []
    chunk_index = 0

    for page in pages:
        page_text = page.text.replace("\r\n", "\n")
        paragraphs = [part.strip() for part in _PARAGRAPH_SPLIT_RE.split(page_text) if part.strip()]

        current_parts: list[str] = []
        current_length = 0

        for paragraph in paragraphs:
            normalized = normalize_whitespace(paragraph)
            if not normalized:
                continue

            if len(normalized) > target_chars:
                if current_parts:
                    chunks.append(
                        ChunkDraft(
                            content="\n\n".join(current_parts),
                            page_number=page.page_number,
                            chunk_index=chunk_index,
                            language=language,
                            keywords=[],
                        )
                    )
                    chunk_index += 1
                    current_parts = []
                    current_length = 0

                for split_part in _split_oversized_text(normalized, target_chars):
                    split_part = normalize_whitespace(split_part)
                    if not split_part:
                        continue
                    chunks.append(
                        ChunkDraft(
                            content=split_part,
                            page_number=page.page_number,
                            chunk_index=chunk_index,
                            language=language,
                            keywords=[],
                        )
                    )
                    chunk_index += 1
                continue

            projected_length = current_length + len(normalized) + (2 if current_parts else 0)
            if current_parts and projected_length > target_chars:
                chunks.append(
                    ChunkDraft(
                        content="\n\n".join(current_parts),
                        page_number=page.page_number,
                        chunk_index=chunk_index,
                        language=language,
                        keywords=[],
                    )
                )
                chunk_index += 1
                current_parts = [normalized]
                current_length = len(normalized)
            else:
                current_parts.append(normalized)
                current_length = projected_length

        if current_parts:
            chunks.append(
                ChunkDraft(
                    content="\n\n".join(current_parts),
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                    language=language,
                    keywords=[],
                )
            )
            chunk_index += 1

    return chunks
