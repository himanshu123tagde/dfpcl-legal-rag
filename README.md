## Project overview (POC → scalable foundation)

You are building a **legal RAG backend on Azure** that follows the architecture in your document:

- **Two-database design**
  - **Azure Cosmos DB**: 1 record per document (metadata, RBAC tags, full summary, status, version, blob path, chunk_count)
  - **Azure AI Search**: N chunk records per document (chunk text + 3072-dim embeddings + page refs + doc_id FK)
  - Linked by **`doc_id`**

- **Two-stage retrieval**
  1. **Stage 1 (Cosmos DB)**: metadata + keyword + RBAC + classification filtering → candidate `doc_id`s + titles + summaries
  2. **Stage 2 (AI Search)**: hybrid vector+BM25 scoped to candidate doc_ids → top chunks for grounding

- **Ingestion pipeline (event-driven)**
  - Upload to **Blob** (tags: department/team/classification/doc_type/language/upload_user)
  - **Event/Queue** message to **Service Bus**
  - Worker extracts text, chunks, embeds, writes:
    - Cosmos doc record + summary/metadata
    - AI Search chunk records

- **Model strategy (India residency safe)**
  - For strict residency in POC: **GPT-4.1 Regional + text-embedding-3-large Regional**
  - Keep config switchable to GPT-5.4 later

This backend POC is designed so you can scale into production (Container Apps workers, retries, idempotency, RBAC filters, caching) without rewriting core modules.

---

## Current backend code structure (FastAPI + workers)

Below is the recommended **backend-only** structure (POC-ready, scalable, not over-engineered). This is the structure you should implement now.

```text
backend/
├─ README.md
├─ pyproject.toml                 # or requirements.txt
├─ .env.example
├─ app/
│  ├─ main.py                     # FastAPI app entrypoint
│  ├─ config.py                   # env-driven settings (Azure endpoints, model deployments, names)
│  ├─ dependencies.py             # DI: current_user, clients, repos/services
│  ├─ routes/
│  │  ├─ __init__.py
│  │  ├─ ingestion.py             # POST /documents/upload, GET /documents/{doc_id}
│  │  ├─ query.py                 # POST /query, (optional) /query/stream
│  │  └─ admin.py                 # /health, /reindex (optional), /metrics (optional)
│  ├─ models/
│  │  ├─ __init__.py
│  │  ├─ documents.py             # Cosmos doc schema (includes id + doc_id)
│  │  ├─ chunks.py                # AI Search chunk schema
│  │  ├─ queries.py               # query request/response + citations
│  │  └─ users.py                 # user claims for RBAC (dept/team/clearance)
│  ├─ repositories/               # thin data-access layer (keeps services clean)
│  │  ├─ __init__.py
│  │  ├─ cosmos_documents_repo.py  # CRUD + metadata search
│  │  └─ search_chunks_repo.py     # chunk indexing + search
│  ├─ services/                   # integrations + cross-cutting services
│  │  ├─ __init__.py
│  │  ├─ openai_service.py         # AzureOpenAI wrapper: chat + embeddings
│  │  ├─ storage_service.py        # Blob upload/download (SDK, not public URLs)
│  │  ├─ bus_service.py            # Service Bus enqueue/dequeue (JSON messages)
│  │  ├─ doc_intelligence_service.py# (later) OCR/layout extraction
│  │  ├─ redis_service.py          # (later) semantic cache + conversation memory
│  │  └─ auth_service.py           # (POC) header-based user; later Entra ID
│  ├─ ingestion/
│  │  ├─ __init__.py
│  │  ├─ router.py                 # MIME routing: pdf/docx/xlsx
│  │  ├─ extractors/
│  │  │  ├─ __init__.py
│  │  │  ├─ pdf_extractor.py       # POC: pypdf; later Doc Intelligence
│  │  │  ├─ word_extractor.py      # later
│  │  │  ├─ excel_extractor.py     # later
│  │  │  └─ image_extractor.py     # later
│  │  ├─ language_detection.py     # later: para-level EN/HI tagging
│  │  ├─ chunking.py               # POC: paragraph; later legal-aware by doc_type
│  │  ├─ metadata_llm.py           # summary + structured metadata extraction (nano later)
│  │  └─ pipeline.py               # orchestrates ingestion steps + status updates
│  ├─ retrieval/
│  │  ├─ __init__.py
│  │  ├─ query_analysis.py         # intent + filters + optimized query text
│  │  ├─ stage1_metadata.py        # Cosmos Stage 1: RBAC+filters -> candidates + summaries
│  │  ├─ stage2_vector.py          # AI Search Stage 2: scoped hybrid search
│  │  └─ context_builder.py        # dedupe/merge + citations + include summaries
│  ├─ generation/
│  │  ├─ __init__.py
│  │  ├─ prompts.py                # legal system prompt templates
│  │  ├─ generator.py              # answer generation (GPT-4.1 in POC)
│  │  └─ validator.py              # (later) groundedness + citation validation
│  ├─ security/
│  │  ├─ __init__.py
│  │  ├─ rbac.py                   # dept/team + classification clearance -> Cosmos filters
│  │  └─ pii.py                    # (later) redact-before-index option
│  ├─ telemetry/
│  │  ├─ __init__.py
│  │  ├─ logging.py                # structured logs
│  │  ├─ metrics.py                # POC counters; later AppInsights
│  │  └─ tracing.py                # later OpenTelemetry
│  └─ utils/
│     ├─ __init__.py
│     ├─ azure_clients.py          # client factories (Cosmos, Search, Blob, Bus)
│     ├─ id_generator.py           # doc_id/chunk_id (UUID/ULID)
│     └─ text_utils.py             # normalization helpers
├─ workers/
│  ├─ ingestion_worker.py          # reads Service Bus, runs ingestion.pipeline
│  └─ reindex_worker.py            # later: versioning/reindex
├─ scripts/
│  ├─ init_cosmos.py               # create db/containers + indexing policy if needed
│  ├─ init_ai_search_index.py      # create/update index schema (vector config)
│  └─ seed_sample_docs.py          # optional POC seed
└─ tests/
   ├─ unit/
   └─ integration/
```

### Key “must be correct” design choices reflected above
- Cosmos items must include **`id`** (Cosmos required). Use `id == doc_id` to simplify.
- Ingestion workers should **download blobs using Blob SDK** (not `httpx.get(blob_url)`), to remain compatible with **Private Endpoints** later.
- Stage 2 scoping should use AI Search-safe filtering, ideally **`search.in(doc_id, 'a,b,c', ',')`**.

---

## Phased implementation plan (POC first, scalable later)

### Phase 0 — Scaffold + runtime configuration
**Goal:** runnable FastAPI project with clean settings, dependency injection, and health endpoints.

**Deliverables**
- `app/main.py` mounts routers
- `app/config.py` reads env
- `.env.example`
- `GET /health` works

**Technical details**
- Use Pydantic settings (`BaseSettings`) for:
  - Azure endpoints/keys
  - model deployment names
  - DB/container/index names
- Decide and lock naming:
  - Cosmos DB name: `legal-rag`
  - Cosmos container: `documents`
  - AI Search index: `legal-chunks`
  - Blob container: `legal-docs`
  - Service Bus queue: `ingestion-queue`

---

### Phase 1 — Azure OpenAI integration (chat + embeddings)
**Goal:** confirm model connectivity early (de-risk biggest dependency).

**Deliverables**
- `services/openai_service.py` using **AzureOpenAI client**
- Test endpoint or internal check that:
  - embeddings return **3072 dims** for `text-embedding-3-large`
  - chat completion works for GPT-4.1 Regional

**Technical details**
- Use modern SDK pattern:
  - `from openai import AzureOpenAI`
  - `client.chat.completions.create(...)`
  - `client.embeddings.create(...)`
- Configuration supports:
  - `AZURE_OPENAI_DEPLOYMENT_GPT=gpt-4.1`
  - `AZURE_OPENAI_DEPLOYMENT_EMBED=text-embedding-3-large`

---

### Phase 2 — Cosmos DB metadata layer (document records + Stage 1 skeleton)
**Goal:** store document metadata + status lifecycle and perform basic metadata searches.

**Deliverables**
- `models/documents.py` includes required fields + Cosmos `id`
- `repositories/cosmos_documents_repo.py`
  - `upsert_document()`
  - `get_document(doc_id)`
  - `search_documents(filters, keyword, rbac_claims)` (basic version)
- Status transitions stored in Cosmos:
  - `uploaded` → `extracting` → `summarized` → `completed` (+ `failed`)

**Technical details**
- Cosmos schema should include (minimum POC):
  - `id`, `doc_id`, `title`, `doc_type`, `keywords`, `full_summary`
  - `department`, `team`, `classification`
  - `status`, `chunk_count`, `blob_path`, timestamps
- Partition key: `/doc_id` (matching the architecture), but ensure `id` exists.

---

### Phase 3 — AI Search chunk index + indexing operations
**Goal:** create the vector index and support chunk upserts.

**Deliverables**
- `scripts/init_ai_search_index.py` creates/updates index:
  - `chunk_id` key
  - `doc_id` filterable
  - `content` searchable
  - `content_vector` (3072 dim, HNSW cosine)
  - `page_number`, `chunk_index`, `language`, `keywords`
- `repositories/search_chunks_repo.py`
  - `upload_chunks(chunks)`
  - `hybrid_search_scoped(query_text, query_vector, doc_id_candidates)`

**Technical details**
- Scoping filter:
  - Prefer: `search.in(doc_id, 'id1,id2,id3', ',')`
- Keep the search call “hybrid-ready”:
  - `search_text=optimized_query`
  - plus `vector` in the same request
  - semantic ranker can be enabled later without changing the interface

---

### Phase 4 — Minimal RAG vertical slice (single-stage milestone)
**Goal:** prove that chunks → retrieval → grounded answer works, before building full ingestion.

**Deliverables**
- `POST /query`:
  - embed question
  - AI Search vector/hybrid search (unscoped)
  - assemble context + citations
  - GPT answer using “use only provided context” prompt

**Technical details**
- This phase is a *temporary milestone* to prove the RAG loop.
- Use a seed script to insert a few chunks into AI Search.

(You can skip this phase if you prefer going directly to ingestion, but it’s useful for fast validation.)

---

### Phase 5 — Ingestion pipeline (Blob + Service Bus + worker) for PDF text (POC)
**Goal:** implement real ingestion with one format first (PDF text-based), using an async worker.

**Deliverables**
- `POST /documents/upload`:
  - uploads file bytes to Blob
  - writes Cosmos record (`status='uploaded'`)
  - enqueues Service Bus message with:
    ```json
    {
      "doc_id": "...",
      "container": "legal-docs",
      "blob_name": "department/doc_type/year/filename.pdf"
    }
    ```
- `workers/ingestion_worker.py`:
  - reads message
  - sets Cosmos status to `extracting`
  - downloads blob via Blob SDK
  - extracts text (POC: `pypdf`)
  - chunks (POC: paragraph chunking)
  - embeddings (text-embedding-3-large)
  - uploads chunks to AI Search
  - generates summary+metadata (POC: optional; can be delayed to Phase 6)
  - updates Cosmos: `status='completed'`, `chunk_count=N`

**Technical details / correctness adjustments**
- Do **not** rely on downloading a public `blob_url` if you want Private Endpoint compatibility.
- Implement **idempotency** at least at doc level:
  - if doc already `completed` and same version/hash, skip
- Blob naming:
  - container: `legal-docs`
  - blob_name: `{department}/{doc_type}/{year}/{doc_id}-{original_filename}`

---

### Phase 6 — Two-stage retrieval (Cosmos → AI Search) aligned to architecture
**Goal:** implement the real retrieval strategy from the document.

**Deliverables**
- `retrieval/query_analysis.py`
  - POC: heuristic rules for doc_type/party/date
  - Later: call nano model to output structured filters + optimized query text
- `retrieval/stage1_metadata.py`
  - Cosmos search applies:
    - keyword match (title/keywords/parties)
    - filters (doc_type/jurisdiction/date_range)
    - RBAC (department/team)
    - classification clearance
  - returns candidate docs including **full_summary**
- `retrieval/stage2_vector.py`
  - scoped hybrid search in AI Search using candidate doc_ids
- `retrieval/context_builder.py`
  - selects top chunks
  - builds citations (doc_id + page_number + chunk_index)
  - **appends doc summaries from Stage 1** as supplementary context (as per architecture)

**Technical details**
- Fallback behavior:
  - if Stage 1 returns 0 → relax filters and retry
  - if still 0 → unscoped search (full index)

---

### Phase 7 — Hardening toward production (optional after POC works)
**Goal:** add the architecture features that matter for enterprise readiness.

**Additions**
- **Document Intelligence OCR/layout** (scanned PDFs + tables)
- **Legal-aware chunking** by doc_type (contracts clause-level, judgments sections, regulations articles)
- **Validation step** with nano model (groundedness + citation accuracy)
- **Redis**
  - conversation memory (last 10 messages, TTL 2h)
  - semantic cache keyed by (query_embedding_hash + RBAC filter), TTL policy
- **Observability**
  - structured logging + metrics (Stage 1 zero-result rate, P95 latency, ingestion failures)
- **Versioning**
  - new upload increments version, soft-delete old chunks, invalidate cache by doc_id

---

## What this POC will produce (end state after Phase 6)

### APIs
- `POST /documents/upload` → returns `doc_id` and queues ingestion
- `GET /documents/{doc_id}` → shows status + metadata + chunk_count
- `POST /query` → two-stage retrieval answer with citations

### Data stored
- **Blob**: raw originals
- **Cosmos**: doc metadata + summaries + RBAC tags + lifecycle status
- **AI Search**: chunk records with vectors and references

### Retrieval behavior (matching your document)
- Stage 1 narrows to ~5–50 docs (typical)
- Stage 2 runs scoped hybrid search (cheaper, more precise)
- Generation is grounded and citation-driven

---

If you want, I can also provide a **“Definition of Done” checklist per phase** (commands to run, expected records in Cosmos/AI Search, and test queries) so you can validate each phase before moving forward.

---

## Execution checklist from here (Phase 4 onward)

You have already completed the foundation through **Phase 3**. The recommended delivery order from here is:

1. **Phase 4**: minimal RAG query path
2. **Phase 5**: real document ingestion
3. **Phase 6**: two-stage retrieval
4. **Phase 7**: retrieval quality + metadata intelligence
5. **Phase 8**: auth, security, and policy hardening
6. **Phase 9**: production scalability and operations

### Cross-phase engineering rules

These rules should hold for every phase so the codebase stays scalable and aligned with SOLID principles:

- **Single Responsibility**: routes handle HTTP only, repositories handle storage/search only, services wrap external SDKs only, orchestration lives in dedicated pipeline/query modules.
- **Open/Closed**: add new extractors, chunkers, auth providers, and retrieval strategies by implementing new modules instead of rewriting shared flow.
- **Liskov Substitution**: keep repository/service interfaces stable so mocks or future Azure-specific implementations can be swapped safely.
- **Interface Segregation**: prefer small focused modules over large service classes that know everything.
- **Dependency Inversion**: business flow should depend on app-level abstractions, not directly on Azure SDK calls spread across the codebase.

Additional guardrails:

- Keep `routes/` thin and deterministic.
- Keep external-client creation in one place.
- Prefer pure helper functions for context building, prompt building, and ranking logic.
- Make failures observable with clear logs and request IDs.
- Design APIs and worker messages so new phases extend them instead of breaking them.
- Add idempotency before scaling throughput.

### Phase 4 checklist — minimal RAG vertical slice

**Goal**
- Prove the end-to-end legal RAG loop with indexed chunks before building the full ingestion pipeline.

**Implementation checklist**
- Replace the current LLM-only `/query` implementation with:
  - embedding generation for the user question
  - unscoped hybrid search against `legal-chunks`
  - context assembly from top chunks
  - grounded answer generation using only retrieved context
- Return clean citations with:
  - `doc_id`
  - `page_number`
  - `chunk_index`
- Keep Phase 4 independent from Cosmos Stage 1 so it remains a fast validation milestone.
- Keep orchestration modular so Stage 1 can be inserted later without rewriting the route.

**Definition of Done**
- `POST /query` works against seeded AI Search chunks.
- Empty search results return a safe “insufficient indexed context” response.
- Prompting explicitly prevents unsupported legal conclusions.
- Response includes citations tied to returned chunks.
- Query logic is separated from the HTTP route.

**Manual validation**
- Seed at least 3 to 5 legal chunks with different topics.
- Ask one direct factual query, one vague query, and one no-match query.
- Confirm the answer uses retrieved context and does not invent case facts.
- Confirm citations map to the retrieved chunk metadata.

### Phase 5 checklist — ingestion pipeline

**Goal**
- Ingest real PDF documents asynchronously through Blob + Service Bus + worker.

**Implementation checklist**
- `POST /documents/upload` uploads file bytes to Blob.
- Create Cosmos record with `status='uploaded'`.
- Enqueue message with `doc_id`, container, and blob name.
- Worker downloads file through Blob SDK, extracts text, chunks content, embeds chunks, uploads them to AI Search, and updates Cosmos.
- Add idempotency using document hash or version-aware processing.

**Definition of Done**
- Uploading a PDF creates a searchable document asynchronously.
- Cosmos status transitions are visible.
- Worker failure paths mark documents as `failed` with diagnostic detail.

### Phase 6 checklist — two-stage retrieval

**Goal**
- Match the target architecture: Cosmos narrowing first, AI Search grounding second.

**Implementation checklist**
- Add query analysis for keyword and filter extraction.
- Implement Cosmos Stage 1 metadata candidate search with RBAC and classification filters.
- Implement scoped hybrid Stage 2 search using candidate `doc_id`s.
- Add a context builder that merges top chunks with document summaries.
- Add fallback behavior when Stage 1 returns no candidates.

**Definition of Done**
- Stage 1 returns candidate documents with summaries.
- Stage 2 searches only those candidate `doc_id`s when available.
- Final answers are grounded in scoped chunks and enriched by document summaries.

### Phase 7 checklist — retrieval quality

**Goal**
- Improve legal relevance and search precision without changing the core architecture.

**Implementation checklist**
- Add richer metadata extraction and better document summaries.
- Introduce legal-aware chunking by `doc_type`.
- Improve query optimization with heuristics first, then optional lightweight model assistance.
- Add optional groundedness and citation validation.

**Definition of Done**
- Retrieval quality improves on real legal/business queries.
- Metadata filters materially improve candidate narrowing.
- Chunk boundaries better preserve clause- or section-level meaning.

### Phase 8 checklist — security and policy hardening

**Goal**
- Make the system safe for real internal usage.

**Implementation checklist**
- Replace header-based user simulation with enterprise identity.
- Enforce RBAC and classification filtering consistently.
- Add secure secret management and audit-friendly logging.
- Add optional pre-index redaction for sensitive content.

**Definition of Done**
- Access control is enforced before retrieval and generation.
- Sensitive documents cannot leak through search or context assembly.

### Phase 9 checklist — production scale and operations

**Goal**
- Make the platform operable, measurable, and scalable under real load.

**Implementation checklist**
- Add Redis for semantic caching and short conversation memory.
- Add metrics, traces, and latency/error dashboards.
- Add versioning and reindex flows for document updates.
- Containerize API and workers for independent scaling.
- Add CI/CD and infrastructure automation.

**Definition of Done**
- API and worker scaling are independent.
- Reindexing and document version updates do not corrupt retrieval.
- Operators can track ingestion failures, query latency, and zero-result rates.