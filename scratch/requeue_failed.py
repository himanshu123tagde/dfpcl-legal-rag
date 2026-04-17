from app.config import get_settings
from app.repositories.cosmos_documents_repo import CosmosDocumentsRepository
from app.services.bus_service import BusService
from app.models.ingestion import IngestionMessage

def requeue_failed_docs():
    settings = get_settings()
    repo = CosmosDocumentsRepository(settings)
    bus = BusService(settings)
    
    container = repo._container
    # Query for all failed documents
    query = "SELECT * FROM c WHERE c.status = 'failed'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    print(f"Found {len(items)} failed documents.")
    
    for item in items:
        doc_id = item.get("doc_id")
        blob_path = item.get("blob_path")
        content_hash = item.get("content_hash")
        mime_type = item.get("mime_type")
        
        if not blob_path:
            print(f"Skipping {doc_id} - no blob path found.")
            continue
            
        print(f"Re-queueing {doc_id}...")
        
        # Reset status and remove failure reason
        item["status"] = "uploaded"
        item["failure_reason"] = None
        # Upsert back to Cosmos
        container.upsert_item(item)
        
        # Parse container and blob_name from blob_path
        # format: container/blob_name...
        parts = blob_path.split("/", 1)
        blob_container = parts[0]
        blob_name = parts[1] if len(parts) > 1 else ""
        
        # Enqueue to service bus
        msg = IngestionMessage(
            doc_id=doc_id,
            container=blob_container,
            blob_name=blob_name,
            content_hash=content_hash,
            mime_type=mime_type,
        )
        bus.enqueue_ingestion(msg)
        print(f"Enqueued {doc_id} successfully.")

if __name__ == "__main__":
    requeue_failed_docs()
