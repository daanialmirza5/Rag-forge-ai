# RAGForge AI

Multi-tenant **Retrieval-Augmented Generation (RAG) SaaS Platform** with hybrid semantic + keyword search, cross-encoder reranking, LangGraph state orchestration, and verifiable citations.

[![CI](https://github.com/daanialmirza5/Rag-forge-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/daanialmirza5/Rag-forge-ai/actions/workflows/ci.yml)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js&logoColor=white)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Vector_DB-Qdrant-DC2626?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-1C3C3C)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **Status**: Feature-complete through security review and performance hardening. The full backend test suite (71 tests) passes against live Postgres/Redis/Qdrant service containers. See [`docs/PROGRESS.md`](docs/PROGRESS.md) for verification logs.

---

## Overview

Most RAG demos are toy scripts limited to basic top-k cosine similarity on a single document. **RAGForge AI** is built as a multi-tenant SaaS architecture designed for real-world enterprise documents:
- **Multi-Tenant Isolation**: Multi-level hierarchy (`Organization` → `Workspace` → `Documents` → `Chunks`) with tenant-scoped payload filtering in Qdrant and relational metadata in PostgreSQL.
- **Hybrid Retrieval & Reranking**: Combines dense semantic vector embeddings (Voyage AI or local Ollama) with sparse keyword retrieval and cross-encoder reranking (`rerank-2`) before context injection.
- **Inspectable State Machine**: Implemented via LangGraph (`Retrieve` → `Rerank` → `Generate` → `Verify & Cite`) with full per-step execution traces.
- **Asynchronous Ingestion**: Offloads document parsing, OCR, recursive text chunking, and embedding generation to background Celery workers backed by Redis.

---

## Architecture

```mermaid
flowchart TD
    subgraph Frontend ["Web Client (Next.js 15 + Tailwind + shadcn/ui)"]
        Dashboard[Workspace Dashboard]
        ChatUI[RAG Chat & Citation Explorer]
        AdminPanel[Organization & Usage Admin]
    end

    subgraph API ["Gateway & API Layer (FastAPI)"]
        AuthRouter[/api/v1/auth - JWT & OAuth2/]
        DocRouter[/api/v1/documents - Ingestion Trigger/]
        ChatRouter[/api/v1/chat - Query & Streaming/]
        LangGraphEngine[LangGraph State Machine\nRetrieve → Rerank → Generate → Cite]
    end

    subgraph Workers ["Async Processing (Celery)"]
        IngestionWorker[Document Parsing & OCR]
        ChunkingEngine[Recursive Chunking & Tokenizer]
        EmbeddingWorker[Embedding Dispatcher]
    end

    subgraph Storage ["Datastores & Queues"]
        Postgres[(PostgreSQL 16\nTenants | Workspaces | Chunks | Chat)]
        Qdrant[(Qdrant Vector DB\nHNSW Index + Tenant Filters)]
        Redis[(Redis\nCelery Broker & Rate Limiting)]
    end

    Frontend -->|JWT Bearer Auth| API
    DocRouter -->|Push Task| Redis
    Redis --> Workers
    Workers -->|Store Vectors| Qdrant
    Workers -->|Store Metadata| Postgres
    ChatRouter --> LangGraphEngine
    LangGraphEngine -->|Hybrid Search| Qdrant
    LangGraphEngine -->|Fetch History & Meta| Postgres
```

---

## Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| **Backend API** | FastAPI (Python 3.12, async) | Asynchronous I/O-bound throughput, native Pydantic v2 validation |
| **Relational DB** | PostgreSQL 16 | ACID transactions for tenants, users, documents, messages, and usage billing |
| **Vector Database** | Qdrant | Dedicated HNSW ANN index with payload filtering per tenant/workspace |
| **Cache & Queue** | Redis | High-speed Celery task broker, rate limiting, and session cache |
| **Async Workers** | Celery | Asynchronous ingestion pipeline (PDF parsing, OCR, chunking, embedding) |
| **LLM Inference** | Anthropic Claude (`claude-3-5-sonnet`) or Ollama (`llama3.1:8b`) | Query rewriting, synthesis, and citation generation (swappable provider) |
| **Embeddings** | Voyage AI (`voyage-3-large`) or Ollama (`nomic-embed-text`) | High-dimensional dense embeddings with provider abstraction |
| **Reranking** | Voyage AI Rerank (`rerank-2`) or Passthrough | Cross-encoder reranking of hybrid search candidate documents |
| **Orchestration** | LangGraph | Deterministic, inspectable RAG state machine |
| **Frontend** | Next.js 15 (App Router) + TypeScript + Tailwind | Responsive dashboard, streaming chat UI, and administrative telemetry |
| **Monitoring** | Prometheus + Grafana, structlog | Real-time service metrics and structured audit logging |
| **CI/CD** | GitHub Actions | Automated linting, type-checking, and service-container integration tests |

---

## Repository Layout

```text
Rag-forge-ai/
├── backend/                  # FastAPI service, Celery workers, Alembic migrations, test suite
├── frontend/                 # Next.js 15 App Router client application
├── infra/                    # Prometheus configuration, Grafana dashboards
├── docs/                     # Technical architecture, database schemas, progress logs
├── .github/workflows/        # Automated CI/CD workflows
├── docker-compose.yml        # Multi-container local deployment
├── .env.example              # Environment variables template
├── LICENSE                   # MIT License
└── README.md
```

---

## Quickstart

### Option A — Free Local Stack (Ollama)

```bash
# 1. Pull local models in Ollama
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# 2. Configure environment and launch containers
cp .env.example .env
docker compose up --build
```

### Option B — Cloud Providers (Claude + Voyage AI)

```bash
cp .env.example .env
# Set ANTHROPIC_API_KEY and VOYAGE_API_KEY in .env:
# LLM_PROVIDER=anthropic, EMBEDDING_PROVIDER=voyage, EMBEDDING_DIMENSIONS=1024, RERANK_PROVIDER=voyage
docker compose up --build
```

Once running:
- **Web Application**: [http://localhost:3000](http://localhost:3000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Prometheus Metrics**: [http://localhost:9090](http://localhost:9090)
- **Grafana Telemetry**: [http://localhost:3002](http://localhost:3002)

---

## Testing & Quality

Execute the backend test suite against live test service containers:

```bash
cd backend
pytest tests/ -v
```

Continuous integration runs automatically on push via [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

---

## Documentation

- [System Architecture](docs/ARCHITECTURE.md)
- [Database Schema & ERD](docs/DATABASE.md)
- [Engineering Progress Log](docs/PROGRESS.md)

---

## License

This project is licensed under the [MIT License](LICENSE).
