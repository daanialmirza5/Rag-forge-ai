# RAG Forge AI — Technical Debt & Architectural Audit

**Repository**: `Rag-forge-ai`  
**Status**: Tier 2 Supporting (Passing pytest IR benchmarks)

## Prioritized Debt Items
- **[P1 — High] Asynchronous Document Ingestion Pipeline**: Ingestion of multi-megabyte PDFs runs in-process. Offload chunking and embedding generation to Celery workers.
- **[P2 — Medium] Adaptive Reranker Batching**: Batch cross-encoder inference for concurrent user queries to maximize GPU/CPU utilization.
- **[P3 — Low] Contextual Query Expansion**: Add automatic multi-query expansion using a lightweight local LLM.
