# Database Design

PostgreSQL 16 holds all relational/metadata state. Qdrant holds vector embeddings only (payload-linked back to `document_chunks.id`). Redis holds ephemeral state (cache, rate-limit counters, Celery queues) — nothing here is a system of record.

## Entity-relationship diagram

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ ORGANIZATION_MEMBERS : has
    USERS ||--o{ ORGANIZATION_MEMBERS : belongs_to
    ORGANIZATIONS ||--o{ WORKSPACES : owns
    WORKSPACES ||--o{ WORKSPACE_MEMBERS : has
    USERS ||--o{ WORKSPACE_MEMBERS : belongs_to
    WORKSPACES ||--o{ DOCUMENTS : contains
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : split_into
    DOCUMENTS ||--o{ INGESTION_JOBS : tracked_by
    WORKSPACES ||--o{ CONVERSATIONS : contains
    USERS ||--o{ CONVERSATIONS : starts
    CONVERSATIONS ||--o{ MESSAGES : contains
    MESSAGES ||--o{ MESSAGE_CITATIONS : cites
    DOCUMENT_CHUNKS ||--o{ MESSAGE_CITATIONS : cited_by
    ORGANIZATIONS ||--o{ API_KEYS : issues
    USERS ||--o{ REFRESH_TOKENS : holds
    ORGANIZATIONS ||--o{ USAGE_RECORDS : accrues
    ORGANIZATIONS ||--o{ AUDIT_LOGS : logs

    ORGANIZATIONS {
        uuid id PK
        string name
        string slug UK
        string plan_tier
        jsonb settings
        timestamptz created_at
        timestamptz updated_at
    }
    USERS {
        uuid id PK
        string email UK
        string hashed_password
        string full_name
        bool is_active
        bool is_superuser
        bool email_verified
        timestamptz created_at
        timestamptz updated_at
    }
    ORGANIZATION_MEMBERS {
        uuid id PK
        uuid organization_id FK
        uuid user_id FK
        string role "owner|admin|member"
        timestamptz created_at
    }
    WORKSPACES {
        uuid id PK
        uuid organization_id FK
        string name
        string slug
        string description
        jsonb settings
        timestamptz created_at
        timestamptz updated_at
    }
    WORKSPACE_MEMBERS {
        uuid id PK
        uuid workspace_id FK
        uuid user_id FK
        string role "owner|editor|viewer"
        timestamptz created_at
    }
    DOCUMENTS {
        uuid id PK
        uuid workspace_id FK
        uuid uploaded_by FK
        string filename
        string original_filename
        string mime_type
        bigint size_bytes
        string storage_path
        string status "pending|processing|completed|failed"
        string error_message
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }
    DOCUMENT_CHUNKS {
        uuid id PK
        uuid document_id FK
        uuid workspace_id FK
        int chunk_index
        text content
        int token_count
        uuid vector_id "Qdrant point id"
        int page_number
        jsonb metadata
        timestamptz created_at
    }
    INGESTION_JOBS {
        uuid id PK
        uuid document_id FK
        string status
        string celery_task_id
        string stage
        string error_message
        timestamptz started_at
        timestamptz completed_at
    }
    CONVERSATIONS {
        uuid id PK
        uuid workspace_id FK
        uuid user_id FK
        string title
        timestamptz created_at
        timestamptz updated_at
    }
    MESSAGES {
        uuid id PK
        uuid conversation_id FK
        string role "user|assistant|system"
        text content
        string model_used
        jsonb token_usage
        timestamptz created_at
    }
    MESSAGE_CITATIONS {
        uuid id PK
        uuid message_id FK
        uuid chunk_id FK
        int marker_index
        float relevance_score
    }
    API_KEYS {
        uuid id PK
        uuid organization_id FK
        uuid created_by FK
        string name
        string key_prefix
        string key_hash
        jsonb scopes
        timestamptz last_used_at
        timestamptz expires_at
        timestamptz revoked_at
        timestamptz created_at
    }
    REFRESH_TOKENS {
        uuid id PK
        uuid user_id FK
        string token_hash
        string user_agent
        string ip_address
        timestamptz expires_at
        timestamptz revoked_at
        timestamptz created_at
    }
    USAGE_RECORDS {
        uuid id PK
        uuid organization_id FK
        uuid workspace_id FK
        uuid user_id FK
        string event_type "chat_message|document_ingested|embedding_batch|rerank_call"
        int tokens_input
        int tokens_output
        numeric cost_usd
        jsonb metadata
        timestamptz created_at
    }
    AUDIT_LOGS {
        uuid id PK
        uuid organization_id FK
        uuid user_id FK
        string action
        string resource_type
        uuid resource_id
        string ip_address
        jsonb metadata
        timestamptz created_at
    }
```

## Design notes

- **Primary keys**: UUID v4 everywhere (`uuid_generate_v4()` / app-side `uuid4()`), so IDs are safe to expose in URLs and never leak sequential-ID information about tenant size.
- **Multi-tenancy**: `organizations` is the billing/tenant root. `workspaces` is the unit documents/conversations/search are scoped to (an org can run multiple isolated knowledge bases — e.g. per team or per client). Every downstream table carries `workspace_id` for direct, index-friendly filtering rather than requiring a join through `organizations` on every query.
- **Soft revocation, not deletion**: `refresh_tokens.revoked_at`, `api_keys.revoked_at` — tokens are never hard-deleted so audit trails survive revocation.
- **`document_chunks.vector_id`**: the join key to Qdrant. The chunk's text and metadata live in Postgres (cheap to query/paginate/join for citations); only the embedding vector lives in Qdrant. This avoids ever needing to round-trip Qdrant to render a citation or re-chunk a document.
- **`message_citations`** is a normalized join table (not a JSON blob on `messages`) so citation relevance scores and chunk references are queryable — e.g. "which chunks are cited most often" for analytics.
- **`ingestion_jobs`** is separate from `documents.status` so a document can be re-ingested (new job row) without losing history of prior attempts.
- **Indexes** (created in the first Alembic migration): `workspace_id` on every scoped table, `(email)` unique on `users`, `(organization_id, slug)` unique on `workspaces`, `(conversation_id, created_at)` on `messages` for ordered history fetch, `(key_prefix)` on `api_keys` for fast lookup before hash comparison.
- **JSONB columns** (`settings`, `metadata`, `scopes`, `token_usage`) hold provider-specific or evolving-shape data that doesn't warrant its own migration for every new field (e.g. per-document parser metadata, per-plan feature flags).
- **Row-level tenant isolation** is enforced in the service layer (every repository method takes and filters by `workspace_id`/`organization_id`, and every endpoint re-verifies the path's `workspace_id` against the resolved row rather than trusting existence alone — see `docs/ARCHITECTURE.md` §5). The Phase 9 security review re-audited every list/get/delete endpoint against this pattern and found (and fixed) one gap outside this table's scope — see `docs/PROGRESS.md`. Postgres RLS policies as an additional defense-in-depth layer remain a deliberately deferred hardening item, not implemented in this build.
- **`api_keys` is schema-only** — the table and model exist (for a future programmatic-access feature), but no service or endpoint creates, authenticates, or revokes them yet. Nothing in the running application reads or writes this table today.

## Qdrant collection schema

Single collection `document_chunks` (configurable name), vector size matching the embedding provider's output dimension (1024 for `voyage-3-large`), cosine distance.

Payload per point:

```json
{
  "chunk_id": "uuid — FK back to document_chunks.id",
  "document_id": "uuid",
  "workspace_id": "uuid",
  "organization_id": "uuid"
}
```

`workspace_id` is a payload index (`keyword`) so every search request applies a `must: [{ key: "workspace_id", match: { value: ... } }]` filter — this is the tenant-isolation boundary for vector search.
