from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional


class Chunk(BaseModel):
    chunk_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)

    content: str = Field(min_length=1)

    # 3072 dim for text-embedding-3-large (set in later phases)
    content_vector: Optional[List[float]] = None

    keywords: List[str] = []
    page_number: Optional[int] = None
    chunk_index: int = 0
    language: str = "en"