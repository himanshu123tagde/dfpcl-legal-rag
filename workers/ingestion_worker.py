from __future__ import annotations

import argparse
import logging
import time

from app.config import get_settings
from app.ingestion.pipeline import IngestionPipeline
from app.models.ingestion import IngestionMessage
from app.repositories.cosmos_documents_repo import CosmosDocumentsRepository
from app.repositories.search_chunks_repo import SearchChunksRepository
from app.services.bus_service import BusService
from app.services.openai_service import OpenAIService
from app.services.storage_service import StorageService


def build_pipeline() -> IngestionPipeline:
    settings = get_settings()
    return IngestionPipeline(
        cosmos_repo=CosmosDocumentsRepository(settings),
        search_repo=SearchChunksRepository(settings),
        openai_service=OpenAIService(settings),
        storage_service=StorageService(settings),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Process legal RAG ingestion messages.")
    parser.add_argument("--once", action="store_true", help="Process at most one message and exit.")
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=5,
        help="Sleep interval when the queue is empty.",
    )
    args = parser.parse_args()

    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger("workers.ingestion")

    bus = BusService(settings)
    pipeline = build_pipeline()

    def handle_message(message: IngestionMessage) -> None:
        logger.info("Processing ingestion message for doc_id=%s", message.doc_id)
        doc = pipeline.run(message)
        logger.info(
            "Completed ingestion for doc_id=%s chunk_count=%s status=%s",
            doc.doc_id,
            doc.chunk_count,
            doc.status,
        )

    while True:
        try:
            processed = bus.process_next_ingestion_message(handle_message, max_wait_time=5)
        except Exception:
            logger.exception("Ingestion worker failed while processing a queue message.")
            if args.once:
                raise
            time.sleep(args.poll_interval_seconds)
            continue

        if args.once:
            break

        if not processed:
            time.sleep(args.poll_interval_seconds)


if __name__ == "__main__":
    main()
