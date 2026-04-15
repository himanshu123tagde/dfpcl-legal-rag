from __future__ import annotations

from azure.cosmos import CosmosClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.servicebus import ServiceBusClient
from azure.storage.blob import BlobServiceClient

from app.config import Settings


_cosmos_client: CosmosClient | None = None
_search_index_client: SearchIndexClient | None = None
_search_client_by_index: dict[str, SearchClient] = {}
_blob_service_client: BlobServiceClient | None = None
_service_bus_client: ServiceBusClient | None = None


def get_cosmos_client(settings: Settings) -> CosmosClient:
    global _cosmos_client
    if _cosmos_client is None:
        if not settings.cosmos_endpoint or not settings.cosmos_key:
            raise RuntimeError("Cosmos DB is not configured (COSMOS_ENDPOINT/COSMOS_KEY missing).")
        _cosmos_client = CosmosClient(settings.cosmos_endpoint, credential=settings.cosmos_key)
    return _cosmos_client


def get_search_index_client(settings: Settings) -> SearchIndexClient:
    global _search_index_client
    if _search_index_client is None:
        if not settings.ai_search_endpoint or not settings.ai_search_key:
            raise RuntimeError("AI Search is not configured (AI_SEARCH_ENDPOINT/AI_SEARCH_KEY missing).")
        _search_index_client = SearchIndexClient(
            endpoint=settings.ai_search_endpoint,
            credential=AzureKeyCredential(settings.ai_search_key),
        )
    return _search_index_client


def get_search_client(settings: Settings, index_name: str) -> SearchClient:
    if index_name in _search_client_by_index:
        return _search_client_by_index[index_name]

    if not settings.ai_search_endpoint or not settings.ai_search_key:
        raise RuntimeError("AI Search is not configured (AI_SEARCH_ENDPOINT/AI_SEARCH_KEY missing).")

    client = SearchClient(
        endpoint=settings.ai_search_endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(settings.ai_search_key),
    )
    _search_client_by_index[index_name] = client
    return client


def get_blob_service_client(settings: Settings) -> BlobServiceClient:
    global _blob_service_client
    if _blob_service_client is None:
        if not settings.blob_connection_string:
            raise RuntimeError("Blob Storage is not configured (BLOB_CONNECTION_STRING missing).")
        _blob_service_client = BlobServiceClient.from_connection_string(settings.blob_connection_string)
    return _blob_service_client


def get_service_bus_client(settings: Settings) -> ServiceBusClient:
    global _service_bus_client
    if _service_bus_client is None:
        if not settings.service_bus_connection_string:
            raise RuntimeError("Service Bus is not configured (SERVICE_BUS_CONNECTION_STRING missing).")
        _service_bus_client = ServiceBusClient.from_connection_string(settings.service_bus_connection_string)
    return _service_bus_client