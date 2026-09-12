# RAG Forge AI — Interview Guide & Technical Defense

## 1. Pitches
- **30-Second Pitch**: "RAG Forge AI is a multi-tenant RAG platform that uses hybrid dense-sparse retrieval (BM25 + vector search), cross-encoder reranking, and inspectable LangGraph pipelines to eliminate retrieval failures and hallucinated LLM responses."
- **2-Minute Pitch**: "Standard vector RAG architectures suffer when searching for specific product IDs, exact acronyms, or dense technical documentation. RAG Forge AI solves this by deploying a production hybrid retrieval pipeline. We run dual retrieval across dense embeddings and sparse BM25 indices, merging candidate lists using Reciprocal Rank Fusion. We then pass the top candidates through a neural cross-encoder reranker to score exact semantic alignment before passing compressed context to the generator. The entire flow runs on LangGraph with strict tenant metadata isolation and automated MRR/NDCG benchmark evaluations."

## 2. Key Technical Q&A
- **Q: Why use Reciprocal Rank Fusion (RRF) instead of simple linear score combination?**
  - **A**: Dense cosine similarities and BM25 scores operate on fundamentally different scales and distributions. Normalizing and linearly weighting them requires hyperparameter tuning per dataset. RRF relies purely on rank order positions, providing robust, scale-invariant fusion without manual calibration.
- **Q: How do you guarantee tenant data isolation in vector search?**
  - **A**: We enforce multi-tenancy at the vector storage layer: every vector upsert and query payload includes a non-negotiable `tenant_id` payload filter, enforced by FastAPI dependency injection before any search query reaches the vector database.
