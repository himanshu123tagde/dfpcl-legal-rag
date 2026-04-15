from __future__ import annotations

import uuid


def new_doc_id() -> str:
    return str(uuid.uuid4())


def build_chunk_id(doc_id: str, chunk_index: int) -> str:
    return f"{doc_id}-chunk-{chunk_index:06d}"
