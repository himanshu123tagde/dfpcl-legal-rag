from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=20)


class Citation(BaseModel):
    doc_id: str
    title: Optional[str] = None
    page_number: Optional[int] = None
    chunk_index: Optional[int] = None


class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    used_hyde: bool = False
    used_scoped_search: bool = False