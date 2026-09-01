"""Prompt templates for the RAG pipeline (query rewriting + grounded answer
generation with citations).
"""

from app.ai.graph.state import ContextChunk

QUERY_REWRITE_SYSTEM_PROMPT = """You rewrite a user's latest chat message into a standalone search \
query for a document-retrieval system. Use the conversation history only to resolve references \
(pronouns, "the second one", follow-up questions) — do not answer the question yourself.

Rules:
- Output ONLY the rewritten query text. No preamble, no quotes, no explanation.
- If the latest message is already a standalone question needing no context, return it unchanged \
(lightly cleaned up if needed).
- Keep it concise: a search query, not a restated essay."""


def build_query_rewrite_user_prompt(*, history_text: str, latest_message: str) -> str:
    return (
        f"Conversation so far:\n{history_text}\n\n"
        f"Latest message: {latest_message}\n\n"
        "Standalone search query:"
    )


RAG_SYSTEM_PROMPT = """You are a helpful assistant answering questions using ONLY the provided \
context excerpts from the user's own documents.

Rules:
- Ground every factual claim in the provided context. Do not use outside knowledge to fill gaps.
- Cite sources inline using bracketed numbers matching the excerpt numbers below, e.g. "Revenue \
grew 12% [1]." Cite every excerpt you draw on; cite multiple with "[1][2]" if a claim draws on more \
than one.
- If the context doesn't contain enough information to answer, say so plainly instead of guessing.
- Write directly and concisely. Do not restate the question or describe what you're about to do."""


def build_rag_context_block(chunks: list[ContextChunk]) -> str:
    """`chunks` must already be in final citation order (excerpt N == chunks[N-1])."""
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        page = f", page {chunk['page_number']}" if chunk.get("page_number") else ""
        parts.append(f"[{i}] (from \"{chunk['document_filename']}\"{page})\n{chunk['content']}")
    return "\n\n".join(parts)


def build_rag_user_prompt(*, context_block: str, question: str) -> str:
    return f"Context excerpts:\n\n{context_block}\n\n---\n\nQuestion: {question}"
