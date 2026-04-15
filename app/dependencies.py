from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Header

from app.config import Settings, get_settings
from app.models.users import UserClaims
from app.repositories.cosmos_documents_repo import CosmosDocumentsRepository
from app.repositories.search_chunks_repo import SearchChunksRepository
from app.services.bus_service import BusService
from app.services.openai_service import OpenAIService
from app.services.storage_service import StorageService


def settings_dep() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, settings_dep]


def request_id_dep(x_request_id: str | None = Header(default=None)) -> str:
    return x_request_id or str(uuid.uuid4())


RequestIdDep = Annotated[str, request_id_dep]


def current_user_dep(
    x_user_id: str | None = Header(default=None),
    x_user_department: str | None = Header(default=None),
    x_user_team: str | None = Header(default=None),
    x_user_clearance: str | None = Header(default=None),
) -> UserClaims:
    return UserClaims(
        user_id=x_user_id or "poc-user",
        department=x_user_department,
        team=x_user_team,
        clearance=(x_user_clearance or "confidential"),  # type: ignore
    )


CurrentUserDep = Annotated[UserClaims, current_user_dep]


_openai_svc: OpenAIService | None = None


def openai_service_dep(settings: SettingsDep) -> OpenAIService:
    global _openai_svc
    if _openai_svc is None:
        _openai_svc = OpenAIService(settings)
    return _openai_svc


OpenAIServiceDep = Annotated[OpenAIService, openai_service_dep]


_cosmos_repo: CosmosDocumentsRepository | None = None


def cosmos_repo_dep(settings: SettingsDep) -> CosmosDocumentsRepository:
    global _cosmos_repo
    if _cosmos_repo is None:
        _cosmos_repo = CosmosDocumentsRepository(settings)
    return _cosmos_repo


CosmosRepoDep = Annotated[CosmosDocumentsRepository, cosmos_repo_dep]


_search_repo: SearchChunksRepository | None = None


def search_repo_dep(settings: SettingsDep) -> SearchChunksRepository:
    global _search_repo
    if _search_repo is None:
        _search_repo = SearchChunksRepository(settings)
    return _search_repo


SearchRepoDep = Annotated[SearchChunksRepository, search_repo_dep]


_storage_svc: StorageService | None = None


def storage_service_dep(settings: SettingsDep) -> StorageService:
    global _storage_svc
    if _storage_svc is None:
        _storage_svc = StorageService(settings)
    return _storage_svc


StorageServiceDep = Annotated[StorageService, storage_service_dep]


_bus_svc: BusService | None = None


def bus_service_dep(settings: SettingsDep) -> BusService:
    global _bus_svc
    if _bus_svc is None:
        _bus_svc = BusService(settings)
    return _bus_svc


BusServiceDep = Annotated[BusService, bus_service_dep]