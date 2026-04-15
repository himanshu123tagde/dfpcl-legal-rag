from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class ExtractedDocument:
    pages: list[ExtractedPage]

    @property
    def page_count(self) -> int:
        return len(self.pages)


def extract_pdf_text(file_bytes: bytes) -> ExtractedDocument:
    reader = PdfReader(BytesIO(file_bytes))
    pages: list[ExtractedPage] = []

    for idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(ExtractedPage(page_number=idx, text=text))

    return ExtractedDocument(pages=pages)
