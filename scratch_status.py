import sys
sys.path.insert(0, '.')
from app.config import get_settings
from app.repositories.cosmos_documents_repo import CosmosDocumentsRepository

repo = CosmosDocumentsRepository(get_settings())
docs = list(repo._container.read_all_items())
for d in docs:
    print(f"Doc: {d['doc_id']} Status: {d.get('status', 'none')} Chunks: {d.get('chunk_count', 0)}")
