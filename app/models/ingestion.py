from __future__ import annotations

from pydantic import BaseModel, Field


class IngestionMessage(BaseModel):
    message_version: int = Field(default=1, ge=1)
    doc_id: str = Field(min_length=1)
    container: str = Field(min_length=1)
    blob_name: str = Field(min_length=1)
    content_hash: str | None = None
    mime_type: str | None = None

    @property
    def blob_path(self) -> str:
        return f"{self.container}/{self.blob_name}"


class UploadDocumentResponse(BaseModel):
    doc_id: str
    status: str
    blob_path: str
    queue_name: str
