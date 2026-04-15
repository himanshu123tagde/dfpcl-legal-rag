from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

DocType = Literal["contract", "judgment", "regulation", "correspondence", "other"]
Classification = Literal["public", "internal", "confidential", "restricted"]
Status = Literal["uploaded", "extracting", "extracted", "summarized", "completed", "failed"]


class DocumentMetadata(BaseModel):
    """
    Cosmos DB document model.

    IMPORTANT:
    - Cosmos DB requires a top-level 'id' field (string).
    - We set id == doc_id for simplicity and to align with your architecture.
    """
    id: str
    doc_id: str = Field(min_length=1)

    title: str
    doc_type: DocType = "other"
    parties: List[str] = []
    jurisdiction: Optional[str] = None
    date: Optional[datetime] = None
    language: str = "en"
    keywords: List[str] = []
    full_summary: Optional[str] = None
    mime_type: Optional[str] = None
    content_hash: Optional[str] = None

    # RBAC tags
    department: Optional[str] = None
    team: Optional[str] = None
    classification: Classification = "internal"

    # lifecycle
    status: Status = "uploaded"
    version: int = 1
    chunk_count: int = 0

    # storage refs
    blob_path: Optional[str] = None
    page_count: Optional[int] = None
    failure_reason: Optional[str] = None

    created_at: datetime
    updated_at: datetime