from __future__ import annotations

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes.admin import router as admin_router
from app.routes.query import router as query_router
from app.routes.ingestion import router as ingestion_router


def create_app() -> FastAPI:
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    app = FastAPI(title=settings.api_title, version=settings.api_version)

    # POC-friendly CORS (tighten later)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(admin_router, tags=["admin"])
    app.include_router(query_router, prefix="/query", tags=["query"])
    app.include_router(ingestion_router, prefix="/documents", tags=["documents"])

    return app


app = create_app()