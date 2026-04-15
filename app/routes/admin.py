from __future__ import annotations

from fastapi import APIRouter
from app.config import get_settings

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/version")
async def version():
    s = get_settings()
    return {"service": s.api_title, "version": s.api_version, "environment": s.environment}