"""Compiled LangGraph state machine for the retrieval half of RAG:

    rewrite_query -> hybrid_retrieve -> rerank

Generation and persistence are deliberately **not** graph nodes. LangGraph's
node model is built around discrete state transitions, not raw token
streaming to an HTTP client — forcing token-by-token SSE output through a
graph node means fighting the abstraction with custom stream writers for no
real benefit, since generation has no branching logic to justify being a
node. `app/services/chat_service.py` runs this graph to get the final
`context_chunks`, then calls `LLMProvider.stream(...)` directly and persists
the result itself. The graph is the right tool for the part that actually
has multiple steps/could grow branches (e.g. a future query-decomposition or
no-retrieval-needed shortcut); it's the wrong tool for "stream text to a
socket."

The graph itself holds no per-request state (no DB session, no checkpointer)
— it's compiled once at import time and reused across requests; all
per-invocation dependencies go through `RunnableConfig.configurable`.
"""

import uuid

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.graph.nodes import hybrid_retrieve_node, rerank_node, rewrite_query_node
from app.ai.graph.state import ChatTurn, ContextChunk, RAGState

_graph = StateGraph(RAGState)
_graph.add_node("rewrite_query", rewrite_query_node)
_graph.add_node("hybrid_retrieve", hybrid_retrieve_node)
_graph.add_node("rerank", rerank_node)
_graph.add_edge(START, "rewrite_query")
_graph.add_edge("rewrite_query", "hybrid_retrieve")
_graph.add_edge("hybrid_retrieve", "rerank")
_graph.add_edge("rerank", END)

retrieval_graph = _graph.compile()


async def run_retrieval(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    history: list[ChatTurn],
    user_message: str,
) -> tuple[str, list[ContextChunk]]:
    """Runs rewrite -> hybrid_retrieve -> rerank and returns
    `(rewritten_query, context_chunks)`, ready to hand to generation."""
    initial_state: RAGState = {
        "workspace_id": str(workspace_id),
        "history": history,
        "user_message": user_message,
        "rewritten_query": "",
        "context_chunks": [],
    }
    result = await retrieval_graph.ainvoke(initial_state, config={"configurable": {"db": db}})
    return result["rewritten_query"], result["context_chunks"]
