# RAGForge AI

Production-grade, multi-tenant **Retrieval-Augmented Generation (RAG) SaaS platform**. Upload documents, get hybrid (semantic + keyword) search with reranking and cited answers, all wrapped in a workspace/team-based dashboard with usage analytics and an admin panel.

> Status: feature-complete through code review, security review, and a performance pass — and `docker compose up` has now actually been run end-to-end, with the full backend test suite (71 tests) passing against real Postgres/Redis/Qdrant. See [`docs/PROGRESS.md`](docs/PROGRESS.md) for exactly what's been verified and how.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Backend API | FastAPI (Python 3.12, async) | Async-native, first-class Pydantic validation, great for AI I/O-bound workloads |
| Relational DB | PostgreSQL 16 | Tenant/user/workspace/document metadata, chat history, billing/usage |
| Vector DB | Qdrant | Dedicated ANN index (HNSW) for embeddings at scale, payload filtering per workspace |
| Cache / Queue broker | Redis | Celery broker + result backend, rate limiting, session cache |
| Async workers | Celery | Document ingestion, OCR, chunking, embedding — off the request path |
| LLM | Anthropic Claude (`claude-opus-4-8` default) **or** Ollama (free, local — `llama3.1:8b` etc.) | Generation, query rewriting, agentic RAG steps; swap via `LLM_PROVIDER` |
| Embeddings | Voyage AI (`voyage-3-large` default) **or** Ollama (free, local — `nomic-embed-text`) | Swap via `EMBEDDING_PROVIDER`; changes vector dimensions, see Quickstart |
| Reranking | Voyage AI rerank (`rerank-2`) **or** none (pass-through) | Cross-encoder reranking of hybrid retrieval candidates; `RERANK_PROVIDER=none` has no free equivalent, so it's a no-op |
| Orchestration | LangGraph | Explicit, inspectable RAG state machine (retrieve → rerank → generate → cite) |
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui | Dashboard, chat UI, admin panel |
| Auth | JWT (access + refresh), OAuth2 password flow | Stateless API auth; refresh tokens stored hashed in Postgres |
| Monitoring | Prometheus + Grafana, structlog | Metrics + structured logs |
| CI/CD | GitHub Actions | Lint, type-check, test (real Postgres/Redis/Qdrant service containers), Docker image build verification |
| Deployment | Docker Compose | `docker compose up` brings up the full stack locally |

All provider integrations (LLM, embeddings, reranker, vector store) sit behind an interface in `backend/app/ai/*/base.py` so a provider can be swapped via configuration without touching call sites.

## Repository layout

```
backend/     FastAPI service, Celery workers, Alembic migrations, tests, Dockerfile
frontend/    Next.js app, Dockerfile
infra/       Prometheus scrape config, Grafana provisioning + dashboards
docs/        Architecture, database design, API reference, progress log
.github/     CI/CD workflows
docker-compose.yml
```

## Quickstart

**Option A — free, fully local (no API keys, no cost):**

```bash
# 1. Install Ollama: https://ollama.com
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# 2. Bring up the stack
cp .env.example .env          # already defaults to the Ollama path — no editing needed
docker compose up --build
```

**Option B — real Claude + Voyage (better answer quality, costs money per API call):**

```bash
cp .env.example .env
# edit .env: set ANTHROPIC_API_KEY / VOYAGE_API_KEY, then change
# LLM_PROVIDER=anthropic, EMBEDDING_PROVIDER=voyage, EMBEDDING_DIMENSIONS=1024,
# RERANK_PROVIDER=voyage (see the comments in .env.example)
docker compose up --build
```

Either way, this brings up Postgres, Redis, Qdrant, the FastAPI backend (after running migrations), a Celery worker, the Next.js frontend, Prometheus, and Grafana. Ollama itself runs on your host machine (not in a container) — the backend/worker reach it at `host.docker.internal:11434`, Docker Desktop's DNS name for the host.

- Web app: http://localhost:3000
- API docs: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3002 (anonymous viewer access; admin login is `admin` / `admin` — change `GF_SECURITY_ADMIN_PASSWORD` in `docker-compose.yml` for anything beyond local use)

The first account you register is a regular user in a new organization it owns — there's no self-service way to become a platform superuser (by design). To reach the admin panel (`/admin` in the web app), grant it directly in Postgres once you have an account:

```sql
UPDATE users SET is_superuser = true WHERE email = 'you@example.com';
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Database design](docs/DATABASE.md)
- [Progress log](docs/PROGRESS.md)

## License

MIT — see [LICENSE](LICENSE).
