from __future__ import annotations

from dataclasses import dataclass

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import ContentSettings

from app.config import Settings
from app.utils.azure_clients import get_blob_service_client


@dataclass(frozen=True)
class BlobLocation:
    container: str
    blob_name: str

    @property
    def blob_path(self) -> str:
        return f"{self.container}/{self.blob_name}"


@dataclass
class StorageService:
    settings: Settings

    def __post_init__(self) -> None:
        self._client = get_blob_service_client(self.settings)

    @property
    def default_container(self) -> str:
        return self.settings.blob_container_name

    def upload_bytes(
        self,
        *,
        blob_name: str,
        data: bytes,
        container: str | None = None,
        content_type: str | None = None,
        overwrite: bool = False,
    ) -> BlobLocation:
        target_container = container or self.default_container
        container_client = self._client.get_container_client(target_container)
        try:
            container_client.create_container()
        except ResourceExistsError:
            pass

        blob_client = container_client.get_blob_client(blob_name)
        upload_kwargs = {"overwrite": overwrite}
        if content_type:
            upload_kwargs["content_settings"] = ContentSettings(content_type=content_type)
        blob_client.upload_blob(data, **upload_kwargs)
        return BlobLocation(container=target_container, blob_name=blob_name)

    def download_bytes(self, *, container: str, blob_name: str) -> bytes:
        blob_client = self._client.get_blob_client(container=container, blob=blob_name)
        return blob_client.download_blob().readall()
