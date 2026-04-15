from __future__ import annotations

import uuid

from app.config import get_settings
from app.models.chunks import Chunk
from app.repositories.search_chunks_repo import SearchChunksRepository
from app.services.openai_service import OpenAIService


def main() -> None:
    s = get_settings()

    openai = OpenAIService(s)
    repo = SearchChunksRepository(s)

    doc_id = "doc-seed-001"
    content = "Termination: Either party may terminate this Agreement with 30 days' written notice."

    vec = openai.embed_text(content)

    chunk = Chunk(
        chunk_id=str(uuid.uuid4()),
        doc_id=doc_id,
        content=content,
        content_vector=vec,
        keywords=["termination", "notice"],
        page_number=5,
        chunk_index=0,
        language="en",
    )

    repo.upload_chunks([chunk])
    print("Seed chunk uploaded.")


if __name__ == "__main__":
    main()