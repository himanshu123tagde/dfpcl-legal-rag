import os
from dotenv import load_dotenv

# Azure SDKs
from openai import AzureOpenAI
from azure.cosmos import CosmosClient
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
from azure.servicebus import ServiceBusClient, ServiceBusMessage

load_dotenv()

print("🔍 Starting Azure connectivity tests...\n")

# =========================
# 1. Azure OpenAI Test
# =========================
try:
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )

    # Chat test
    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT"),
        messages=[{"role": "user", "content": "Say OK"}],
        max_tokens=5
    )
    print("✅ OpenAI Chat:", response.choices[0].message.content)

    # Embedding test
    emb = client.embeddings.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_EMBED"),
        input="test"
    )
    print("✅ OpenAI Embedding length:", len(emb.data[0].embedding))

except Exception as e:
    print("❌ OpenAI FAILED:", e)

# =========================
# 2. Cosmos DB Test
# =========================
try:
    cosmos_client = CosmosClient(
        os.getenv("COSMOS_ENDPOINT"),
        os.getenv("COSMOS_KEY")
    )

    db = cosmos_client.get_database_client(os.getenv("COSMOS_DB_NAME"))
    container = db.get_container_client(os.getenv("COSMOS_CONTAINER_DOCUMENTS"))

    test_doc = {
        "id": "test-doc",
        "doc_id": "test-doc",
        "title": "Test Document"
    }

    container.upsert_item(test_doc)

    print("✅ Cosmos DB: write successful")

except Exception as e:
    print("❌ Cosmos FAILED:", e)

# =========================
# 3. Azure AI Search Test
# =========================
try:
    search_client = SearchClient(
        endpoint=os.getenv("AI_SEARCH_ENDPOINT"),
        index_name=os.getenv("AI_SEARCH_INDEX_CHUNKS"),
        credential=AzureKeyCredential(os.getenv("AI_SEARCH_KEY"))
    )

    results = search_client.search(search_text="test", top=1)
    list(results)

    print("✅ AI Search: query successful")

except Exception as e:
    print("❌ AI Search FAILED:", e)

# =========================
# 4. Blob Storage Test
# =========================
try:
    blob_service = BlobServiceClient.from_connection_string(
        os.getenv("BLOB_CONNECTION_STRING")
    )

    container_client = blob_service.get_container_client(
        os.getenv("BLOB_CONTAINER_NAME")
    )

    blob_client = container_client.get_blob_client("test.txt")
    blob_client.upload_blob("hello from test", overwrite=True)

    print("✅ Blob Storage: upload successful")

except Exception as e:
    print("❌ Blob FAILED:", e)

# =========================
# 5. Service Bus Test
# =========================
try:
    sb_client = ServiceBusClient.from_connection_string(
        os.getenv("SERVICE_BUS_CONNECTION_STRING")
    )

    with sb_client:
        sender = sb_client.get_queue_sender(
            queue_name=os.getenv("SERVICE_BUS_QUEUE_INGESTION")
        )
        with sender:
            sender.send_messages(ServiceBusMessage("test message"))

    print("✅ Service Bus: message sent")

except Exception as e:
    print("❌ Service Bus FAILED:", e)

print("\n🎯 Testing complete.")