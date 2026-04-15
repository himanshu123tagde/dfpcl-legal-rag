from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.ingestion.chunking import chunk_pdf_pages
from app.ingestion.extractors.pdf_extractor import extract_pdf_text
from app.models.chunks import Chunk
from app.models.documents import DocumentMetadata
from app.models.ingestion import IngestionMessage
from app.repositories.cosmos_documents_repo import CosmosDocumentsRepository
from app.repositories.search_chunks_repo import SearchChunksRepository
from app.services.openai_service import OpenAIService
from app.services.storage_service import StorageService
from app.utils.id_generator import build_chunk_id


@dataclass
class IngestionPipeline:
    cosmos_repo: CosmosDocumentsRepository
    search_repo: SearchChunksRepository
    openai_service: OpenAIService
    storage_service: StorageService

    def run(self, message: IngestionMessage) -> DocumentMetadata:
        doc = self.cosmos_repo.get_by_doc_id(message.doc_id)
        if not doc:
            raise ValueError(f"Document not found for ingestion: {message.doc_id}")

        if doc.status == "completed" and doc.chunk_count > 0:
            return doc

        try:
            now = datetime.utcnow()
            doc.status = "extracting"
            doc.failure_reason = None
            doc.updated_at = now
            self.cosmos_repo.upsert(doc)

            file_bytes = self.storage_service.download_bytes(
                container=message.container,
                blob_name=message.blob_name,
            )
            extracted = extract_pdf_text(file_bytes)

            doc.status = "extracted"
            doc.page_count = extracted.page_count
            doc.updated_at = datetime.utcnow()
            self.cosmos_repo.upsert(doc)

            chunk_drafts = chunk_pdf_pages(extracted.pages, language=doc.language)
            if not chunk_drafts:
                raise ValueError("No extractable text was found in the PDF.")

            embeddings = self.openai_service.embed_texts([chunk.content for chunk in chunk_drafts])
            if len(embeddings) != len(chunk_drafts):
                raise RuntimeError("Embedding count did not match chunk count.")

            chunks = [
                Chunk(
                    chunk_id=build_chunk_id(doc.doc_id, chunk_draft.chunk_index),
                    doc_id=doc.doc_id,
                    content=chunk_draft.content,
                    content_vector=embedding,
                    keywords=chunk_draft.keywords or [],
                    page_number=chunk_draft.page_number,
                    chunk_index=chunk_draft.chunk_index,
                    language=chunk_draft.language,
                )
                for chunk_draft, embedding in zip(chunk_drafts, embeddings, strict=True)
            ]

            self.search_repo.upload_chunks(chunks)

            doc.status = "completed"
            doc.chunk_count = len(chunks)
            doc.blob_path = message.blob_path
            doc.updated_at = datetime.utcnow()
            self.cosmos_repo.upsert(doc)
            return doc
        except Exception as exc:
            doc.status = "failed"
            doc.failure_reason = str(exc)
            doc.updated_at = datetime.utcnow()
            self.cosmos_repo.upsert(doc)
            raise
