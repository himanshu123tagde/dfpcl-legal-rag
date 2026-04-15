from __future__ import annotations

import unittest

from app.ingestion.chunking import chunk_pdf_pages
from app.ingestion.extractors.pdf_extractor import ExtractedPage
from app.utils.text_utils import sanitize_filename


class Phase5HelperTests(unittest.TestCase):
    def test_chunk_pdf_pages_assigns_page_numbers_and_indices(self) -> None:
        pages = [
            ExtractedPage(
                page_number=1,
                text="Clause 1. Payment terms apply.\n\nClause 2. Termination requires notice.",
            ),
            ExtractedPage(
                page_number=2,
                text="Clause 3. Liability is limited to direct damages.",
            ),
        ]

        chunks = chunk_pdf_pages(pages, target_chars=40)

        self.assertEqual(len(chunks), 3)
        self.assertEqual([chunk.chunk_index for chunk in chunks], [0, 1, 2])
        self.assertEqual([chunk.page_number for chunk in chunks], [1, 1, 2])

    def test_sanitize_filename_normalizes_unsafe_characters(self) -> None:
        sanitized = sanitize_filename("Master Service Agreement (Final) 2026.pdf")
        self.assertEqual(sanitized, "master-service-agreement-final-2026.pdf")


if __name__ == "__main__":
    unittest.main()
