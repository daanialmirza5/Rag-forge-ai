# RAG Forge AI — Engineering Guide & Mastery Document

## 1. What Is RAG Forge AI?
RAG Forge AI is a **production-grade multi-tenant Retrieval-Augmented Generation (RAG) platform**. It combines dense vector retrieval (embeddings), sparse lexical retrieval (BM25), cross-encoder re-ranking, and inspectable LangGraph retrieval pipelines to deliver high-precision document question-answering with verifiable source attribution and multi-tenant data isolation.

## 2. Real-World Problem Solved
1. **Vector-Only Retrieval Blindspots**: Dense embeddings frequently fail on exact keyword searches, product codes, or acronyms.
2. **Context Stuffing & Needle-in-a-Haystack**: Passing unranked chunks to an LLM degrades reasoning quality and increases token latency.
3. **Multi-Tenant Security Leaks**: Mixing tenant vectors in a single shared index without strict metadata filtering causes catastrophic data leaks.
4. **Black-Box RAG Pipelines**: Operators cannot debug why a specific document chunk was retrieved or dropped.

## 3. High-Level Architecture
- **Backend**: FastAPI (Python 3.12), SQLAlchemy 2.0, Alembic migrations.
- **Retrieval Engine**:
  - `hybrid_retriever.py`: Reciprocal Rank Fusion (RRF) combining dense cosine similarity and sparse BM25 scores.
  - `reranker.py`: Cross-encoder neural reranking (`cross-encoder/ms-marco-MiniLM-L-6-v2`) scoring query-chunk relevance pairs.
  - `chunking/`: Semantic and recursive character chunkers with configurable overlap buffers.
- **AI & Orchestration**: LangGraph DAG executing query rewrite, retrieval, rerank, context compression, and grounded generation.
- **Vector DB**: Qdrant / Chroma / pgvector with tenant-isolated collection partitions.

## 4. Algorithmic Formulations
- **Reciprocal Rank Fusion (RRF)**:
  $$\text{RRF}(d) = \frac{1}{k + \text{Rank}_{\text{dense}}(d)} + \frac{1}{k + \text{Rank}_{\text{sparse}}(d)}$$
  where $k = 60$ acts as a smoothing parameter to balance dense and sparse contributions.
- **Cross-Encoder Scoring**: Computes full cross-attention score $s(q, c)$ over the top 25 RRF candidates, selecting the top 5 highest fidelity chunks.

## 5. Security & Multi-Tenancy
- Hard tenant isolation: Every vector query applies mandatory metadata filter `tenant_id == current_tenant.id`.
- Role-based document access controls (Owner, Editor, Viewer).

## 6. Testing Strategy
- Automated pytest IR benchmark suite calculating Mean Reciprocal Rank (MRR@10) and Normalized Discounted Cumulative Gain (NDCG@5).
