from app.config import get_settings
from app.repositories.cosmos_documents_repo import CosmosDocumentsRepository

def check_docs():
    settings = get_settings()
    repo = CosmosDocumentsRepository(settings)
    
    # Use the private _container attribute
    container = repo._container
    query = "SELECT * FROM c ORDER BY c._ts DESC"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    print(f"Total documents: {len(items)}")
    for item in items[:10]:
        print(f"ID: {item.get('id')}, Status: {item.get('status')}, Failure: {item.get('failure_reason')}")

if __name__ == "__main__":
    check_docs()
