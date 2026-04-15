from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from azure.servicebus import ServiceBusMessage

from app.config import Settings
from app.models.ingestion import IngestionMessage
from app.utils.azure_clients import get_service_bus_client


@dataclass
class BusService:
    settings: Settings

    def __post_init__(self) -> None:
        self._client = get_service_bus_client(self.settings)

    @property
    def queue_name(self) -> str:
        return self.settings.service_bus_queue_ingestion

    def enqueue_ingestion(self, message: IngestionMessage) -> None:
        with self._client.get_queue_sender(queue_name=self.queue_name) as sender:
            sender.send_messages(ServiceBusMessage(message.model_dump_json()))

    def _decode_message(self, message: object) -> IngestionMessage:
        raw_body = b"".join(part for part in message.body)
        return IngestionMessage.model_validate_json(raw_body.decode("utf-8"))

    def process_next_ingestion_message(
        self,
        handler: Callable[[IngestionMessage], None],
        *,
        max_wait_time: int = 5,
    ) -> bool:
        """
        Receive and settle a single ingestion message.

        Returning False means the queue was empty during the polling window.
        """
        with self._client.get_queue_receiver(queue_name=self.queue_name, max_wait_time=max_wait_time) as receiver:
            messages = receiver.receive_messages(max_message_count=1, max_wait_time=max_wait_time)
            if not messages:
                return False

            message = messages[0]
            try:
                payload = self._decode_message(message)
                handler(payload)
            except Exception:
                receiver.abandon_message(message)
                raise
            else:
                receiver.complete_message(message)
                return True
