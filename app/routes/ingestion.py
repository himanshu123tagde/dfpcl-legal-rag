from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.dependencies import BusServiceDep, CosmosRepoDep, CurrentUserDep, StorageServiceDep
from app.models.documents import DocumentMetadata
from app.models.ingestion import IngestionMessage, UploadDocumentResponse
from app.utils.id_generator import new_doc_id
from app.utils.text_utils import sanitize_filename, sanitize_path_token

router = APIRouter()


def _ensure_pdf_upload(file: UploadFile) -> None:
    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()
    if content_type == "application/pdf" or filename.endswith(".pdf"):
        return
    raise HTTPException(status_code=400, detail="Phase 5 supports PDF uploads only.")


def _build_blob_name(
    *,
    department: str,
    doc_type: str,
    doc_id: str,
    original_filename: str,
) -> str:
    year = datetime.utcnow().year
    safe_department = sanitize_path_token(department, fallback="general")
    safe_doc_type = sanitize_path_token(doc_type, fallback="other")
    safe_filename = sanitize_filename(original_filename or "document.pdf", fallback_stem=doc_id)
    return f"{safe_department}/{safe_doc_type}/{year}/{doc_id}-{safe_filename}"


@router.post("/upload", response_model=UploadDocumentResponse)
async def upload_document(
    user: CurrentUserDep,
    cosmos: CosmosRepoDep,
    storage: StorageServiceDep,
    bus: BusServiceDep,
    file: UploadFile = File(...),
    department: str = Form(...),
    team: str = Form(...),
    classification: str = Form("internal"),
    doc_type: str = Form("other"),
    language: str = Form("en"),
):
    _ensure_pdf_upload(file)
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    now = datetime.utcnow()
    doc_id = new_doc_id()
    filename = file.filename or "document.pdf"
    content_type = file.content_type or "application/pdf"
    department_value = department or user.department or "general"
    team_value = team or user.team or "general"
    content_hash = sha256(file_bytes).hexdigest()
    blob_name = _build_blob_name(
        department=department_value,
        doc_type=doc_type,
        doc_id=doc_id,
        original_filename=filename,
    )

    try:
        blob = storage.upload_bytes(
            blob_name=blob_name,
            data=file_bytes,
            content_type=content_type,
            overwrite=False,
        )

        doc = DocumentMetadata(
            id=doc_id,
            doc_id=doc_id,
            title=filename,
            doc_type=doc_type,  # type: ignore
            parties=[],
            jurisdiction=None,
            date=None,
            language=language,
            keywords=[],
            full_summary=None,
            mime_type=content_type,
            content_hash=content_hash,
            department=department_value,
            team=team_value,
            classification=classification,  # type: ignore
            status="uploaded",
            version=1,
            chunk_count=0,
            blob_path=blob.blob_path,
            page_count=None,
            failure_reason=None,
            created_at=now,
            updated_at=now,
        )

        cosmos.upsert(doc)

        bus.enqueue_ingestion(
            IngestionMessage(
                doc_id=doc_id,
                container=blob.container,
                blob_name=blob.blob_name,
                content_hash=content_hash,
                mime_type=content_type,
            )
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        try:
            existing = cosmos.get_by_doc_id(doc_id)
            if existing:
                existing.failure_reason = str(e)
                existing.updated_at = datetime.utcnow()
                cosmos.upsert(existing)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Document upload failed.")

    return UploadDocumentResponse(
        doc_id=doc_id,
        status="uploaded",
        blob_path=blob.blob_path,
        queue_name=bus.queue_name,
    )


@router.get("/{doc_id}")
async def get_document(doc_id: str, cosmos: CosmosRepoDep):
    doc = cosmos.get_by_doc_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc.model_dump()


@router.post("/search")
async def search_documents(
    user: CurrentUserDep,
    cosmos: CosmosRepoDep,
    keyword: str = Form(...),
    doc_type: str | None = Form(default=None),
    jurisdiction: str | None = Form(default=None),
):
    """
    Phase 2: POC Stage-1 style metadata search endpoint.
    """
    try:
        docs = cosmos.search_stage1(
            user=user,
            keyword=keyword,
            doc_type=doc_type,
            jurisdiction=jurisdiction,
            limit=25,
        )
        return {
            "count": len(docs),
            "results": [
                {
                    "doc_id": d.doc_id,
                    "title": d.title,
                    "doc_type": d.doc_type,
                    "classification": d.classification,
                    "department": d.department,
                    "team": d.team,
                    "status": d.status,
                    "updated_at": d.updated_at,
                }
                for d in docs
            ],
        }
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))