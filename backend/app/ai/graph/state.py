"""State for the retrieval half of the RAG pipeline (rewrite -> hybrid
retrieve -> rerank). Generation and persistence happen *outside* the graph —
see `app/ai/graph/rag_graph.py` module docstring for why.
"""

from typing import TypedDict


class ChatTurn(TypedDict):
    role: str  # "user" | "assistant"
    content: str


class ContextChunk(TypedDict):
    chunk_id: str
    document_id: str
    document_filename: str
    content: str
    page_number: int | None
    relevance_score: float


class RAGState(TypedDict):
    workspace_id: str
    history: list[ChatTurn]
    user_message: str
    rewritten_query: str
    context_chunks: list[ContextChunk]
