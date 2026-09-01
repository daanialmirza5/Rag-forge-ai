# Architecture

## 1. System overview

RAGForge is a multi-tenant SaaS platform. The tenancy model is:

```
Organization (tenant, billing unit)
 └─ Workspace (project / knowledge base — a tenant can have many)
     ├─ Documents → Chunks (Postgres metadata + Qdrant vectors)
     └─ Conversations → Messages (chat history, cited answers)
```

Every request is scoped by `organization_id` → `workspace_id`. Row-level scoping is enforced in the service layer (not relied on for DB-level RLS in v1, documented as a hardening item in `docs/PROGRESS.md`).

## 2. High-level component diagram

```
                        ┌─────────────────────┐
                        │   Next.js Frontend   │
                        │  (dashboard, chat,    │
                        │   admin panel)        │
                        └──────────┬───────────┘
                                   │ HTTPS / REST (JWT bearer)
                                   ▼
                        ┌─────────────────────┐
                        │   FastAPI Backend     │
                        │  (api/v1/* routers)   │
                        └──┬────────┬────────┬─┘
                           │        │        │
             ┌─────────────┘        │        └───────────────┐
             ▼                      ▼                        ▼
   ┌─────────────────┐   ┌────────────────────┐   ┌────────────────────┐
   │   PostgreSQL 16   │   │      Qdrant         │   │       Redis         │
   │ users, orgs,       │   │  chunk embeddings   │   │ cache, rate-limit,  │
   │ workspaces, docs,  │   │  (HNSW, per-        │   │ Celery broker/      │
   │ chunks (meta),     │   │   workspace         │   │ result backend      │
   │ conversations,     │   │   payload filter)   │   │                     │
   │ messages, usage    │   │                     │   │                     │
   └─────────────────┘   └────────────────────┘   └──────────┬──────────┘
                                                              │
                                                              ▼
                                                    ┌────────────────────┐
                                                    │   Celery Workers     │
                                                    │ parse → OCR → chunk  │
                                                    │ → embed → index      │
                                                    └──────────┬──────────┘
                                                               │
                        ┌──────────────────────────────────────┘
                        ▼
             ┌───────────────────────────────────────────┐
             │              AI Provider Layer               │
             │  LLM: Anthropic Claude (claude-opus-4-8)      │
             │  Embeddings: Voyage AI (voyage-3-large)       │
             │  Rerank: Voyage AI rerank-2                   │
             │  Orchestration: LangGraph RAG state machine   │
             └───────────────────────────────────────────┘
```

## 3. Request lifecycle — document ingestion

1. Client `POST /api/v1/workspaces/{id}/documents` (multipart upload) → backend stores raw file in object storage path (local volume in dev, S3-compatible in prod via `STORAGE_BACKEND` config), writes a `documents` row with `status=pending`, enqueues a Celery task, returns `202` with a document ID.
2. Celery task pipeline (`app/workers/tasks/ingestion_tasks.py`):
   - **Parse** — dispatch to the right parser by MIME type (`app/ai/parsers/*`): PDF (with OCR fallback for scanned pages via Tesseract), DOCX, HTML, Markdown, plain text.
   - **Chunk** — `RecursiveChunker` (`app/ai/chunking/recursive_chunker.py`, built on `langchain-text-splitters`), operating per-page so every chunk keeps an accurate page number for citations. Chunk size/overlap are char-based and configurable (`CHUNK_SIZE_CHARS`/`CHUNK_OVERLAP_CHARS`).
   - **Embed** — batch chunks through the configured embedding provider (`app/ai/embeddings/*`).
   - **Index** — upsert vectors into Qdrant with a payload of `{workspace_id, document_id, chunk_id}` for filtered search; write chunk rows to Postgres with the Qdrant point id.
   - Each stage updates `documents.status` (`processing` → `completed`/`failed`) and `ingestion_jobs` for observability.
3. Frontend polls (or subscribes via SSE, see Phase 5/6) document status until `completed`.

## 4. Request lifecycle — chat / RAG query

Implemented as a LangGraph state machine (`app/ai/graph/rag_graph.py`):

```
 ┌───────────┐   ┌───────────────┐   ┌──────────────┐   ┌─────────────┐   ┌────────────┐
 │ rewrite_   │──▶│ hybrid_        │──▶│  rerank        │──▶│  generate     │──▶│  persist    │
 │ query       │   │ retrieve       │   │ (cross-encoder)│   │ (Claude, cites)│   │ (message +  │
 │ (condense   │   │ (Qdrant ANN +  │   │ top-k → top-n  │   │ streamed       │   │  citations) │
 │  chat hist.)│   │  BM25, RRF)    │   │                │   │  response)     │   │             │
 └───────────┘   └───────────────┘   └──────────────┘   └─────────────┘   └────────────┘
```

- **rewrite_query**: condenses the conversation history + latest user turn into a standalone search query (handles follow-ups like "what about the second one?").
- **hybrid_retrieve**: runs dense (Qdrant cosine) and sparse (BM25 over chunk text, via `rank_bm25`) retrieval in parallel, fuses with Reciprocal Rank Fusion, scoped to `workspace_id`.
- **rerank**: Voyage rerank-2 cross-encoder narrows fused candidates to the top-n most relevant chunks.
- **generate**: Claude generates the answer with the reranked chunks in context, instructed to cite `[n]` markers mapped back to source chunks/documents.
- **persist**: stores the assistant message with structured citations (`document_id`, `chunk_id`, `page_number`) for the frontend to render as clickable references.

## 5. Multi-tenancy & isolation

- Every domain table carries `workspace_id` (and transitively `organization_id`) and every service-layer query filters on it — see `docs/DATABASE.md`.
- Qdrant uses a single collection per deployment with a `workspace_id` payload index; all queries apply a `must` filter on it, so tenants never cross-contaminate the ANN index without needing one collection per tenant.
- JWT access tokens carry `organization_id`; every endpoint that takes a `workspace_id`/`document_id`/`conversation_id` path param re-verifies it belongs to the resolved workspace/organization at the service layer (not just "does this row exist") — this is what closes IDOR-style cross-tenant access, and every such check has a regression test (e.g. `test_document_from_other_workspace_is_not_accessible`).

## 6. Provider abstraction

Every external AI dependency implements a small ABC so it can be swapped by config (`app/core/config.py`) without touching call sites:

- `app/ai/llm/base.py` → `LLMProvider` (`AnthropicProvider`, or `OllamaProvider` — a free, fully local alternative with no API key, selected via `LLM_PROVIDER=ollama`)
- `app/ai/embeddings/base.py` → `EmbeddingProvider` (`VoyageEmbeddingProvider`, `OpenAIEmbeddingProvider`, or `OllamaEmbeddingProvider` — free/local, `EMBEDDING_PROVIDER=ollama`)
- `app/ai/reranking/base.py` → `RerankProvider` (`VoyageRerankProvider`, or `NoOpRerankProvider` — a pass-through fallback for the free path, since there's no simple local equivalent to a hosted cross-encoder reranker; `RERANK_PROVIDER=none`)
- `app/ai/vectorstore/base.py` → `VectorStore` (`QdrantVectorStore`)

The free/local path (Ollama for both LLM and embeddings, no reranking) trades answer quality for zero API cost — this is a deliberate, documented tradeoff for demo/development use, not a claim that a small local model matches Claude's output quality. See the README Quickstart and `.env.example` for how to switch between the two.

## 7. Security model

- Passwords hashed with `bcrypt` directly (not `passlib` — passlib's bcrypt backend is unmaintained and breaks under bcrypt>=4.1; see `docs/PROGRESS.md`). JWT access tokens (short-lived, 15 min default, algorithm pinned — `jwt.decode` is called with an explicit `algorithms=[...]` allowlist, so a token can't force `alg=none` or swap algorithms) + refresh tokens (opaque random string, SHA-256 hash at rest, rotated on use, revocable).
- Two-level RBAC: organization role (`owner`/`admin`/`member`) and per-workspace role (`owner`/`editor`/`viewer`), both enforced as FastAPI dependencies (`app/api/deps.py`) — every mutating endpoint requires at least `editor`, reads require at least `viewer`.
- Superuser admin surface (`/api/v1/admin/*`) is a separate flag (`User.is_superuser`) independent of any organization membership, gated by its own `require_superuser` dependency on every route.
- `SECRET_KEY` is validated at startup: booting with `APP_ENV=production` and the `.env.example` placeholder value raises immediately rather than silently running with a guessable JWT signing key.
- Login doesn't leak whether an email is registered: a nonexistent email still pays bcrypt's verification cost against a dummy hash (equalizes response time) and returns the same generic message as a wrong password.
- Rate limiting middleware: a Redis **fixed-window** counter (not a token bucket) keyed by API key header, bearer token, or client IP, applied to every route except health/metrics/docs.
- All AI provider calls run server-side only; no provider credentials ever reach the frontend.
- Input validation at every API boundary via Pydantic schemas; file uploads are checked against a MIME-type allowlist and a size cap before parsing — note the MIME type is the client-supplied `Content-Type` header, not sniffed from file content, so it's a defense-in-depth check, not a hard content guarantee (see `docs/PROGRESS.md` Known Issues).
- Local file storage resolves every path against its root and rejects anything that escapes it (`Path.is_relative_to`), independent of how the storage key was built.
- The `APIKey` model exists in the schema (for future programmatic/API-key access) but has no service or endpoint yet — it's unused today, not a security surface.

## 8. Observability

- Structured JSON logging (`structlog`) with request-id correlation (`app/middleware/request_context.py`), one line per request with method/path/status/duration — never headers, tokens, or bodies.
- Prometheus: `/metrics` (`prometheus-fastapi-instrumentator`) exposes `http_requests_total`, `http_request_duration_seconds` (labeled by method/handler/status), `http_requests_inprogress`, and request/response size summaries. The chat SSE endpoint's multi-second stream duration is excluded from the latency histogram so it doesn't skew p95/p99.
- Grafana: provisioned via `infra/grafana/` (datasource + a 5-panel "RAGForge API" dashboard — request rate, error rate, latency percentiles, in-flight requests, requests by status class), brought up alongside Prometheus by `docker-compose.yml`.
- Usage/cost accounting (token counts, estimated LLM cost) is tracked separately in Postgres (`usage_records`, written by `app/services/usage_service.py`) and surfaced via the analytics API/dashboard — not as Prometheus metrics.

## 9. Directory layout

```
backend/
  app/
    ai/            LLM/embeddings/reranking/vectorstore providers, RAG graph, parsers, chunking
    api/v1/         endpoints/ (auth, users, organizations, workspaces, documents,
                    conversations, analytics, admin, health) + deps.py (RBAC guards)
    core/           config, security (JWT/bcrypt), logging, exceptions
    db/             session management (pooled for the API, NullPool for Celery workers)
    models/         SQLAlchemy ORM (15 tables — see docs/DATABASE.md)
    schemas/        Pydantic v2 request/response models
    services/       business logic, one module per domain area
    storage/        local/S3 file storage behind a common interface
    workers/        Celery app + the document ingestion task
  alembic/          migrations
  tests/            unit/ (no external deps) + integration/ (real Postgres/Redis/Qdrant)
  Dockerfile
frontend/
  src/
    app/            Next.js App Router pages (auth, dashboard, workspaces/[id]/*, admin)
    components/     ui/ (hand-written primitives), charts/, admin/, chat/, documents/, layout/
    hooks/          React Query hooks per resource
    lib/api/        typed fetch client per resource
    store/          Zustand stores (auth, workspace selection, toasts)
  Dockerfile
infra/
  prometheus/       scrape config
  grafana/          datasource + dashboard provisioning
docs/               this file, DATABASE.md, PROGRESS.md
.github/workflows/  CI (lint, typecheck, test against real service containers, Docker build)
docker-compose.yml  postgres, redis, qdrant, migrate, backend, worker, frontend, prometheus, grafana
```

See the top-level `README.md` for the quickstart; `docs/PROGRESS.md` is the authoritative, continuously-updated record of what's built, what's verified, and what's known-incomplete.
