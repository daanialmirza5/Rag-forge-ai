from app.ai.graph.state import ContextChunk
from app.ai.prompts.rag_prompts import build_rag_context_block, build_rag_user_prompt


def _chunk(**overrides) -> ContextChunk:
    base = ContextChunk(
        chunk_id="chunk-1",
        document_id="doc-1",
        document_filename="report.pdf",
        content="Revenue grew 12% year over year.",
        page_number=3,
        relevance_score=0.9,
    )
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


def test_context_block_numbers_excerpts_starting_at_one():
    block = build_rag_context_block([_chunk(), _chunk(document_filename="notes.txt", page_number=None)])
    assert "[1]" in block
    assert "[2]" in block
    assert block.index("[1]") < block.index("[2]")


def test_context_block_includes_filename_and_page():
    block = build_rag_context_block([_chunk(document_filename="Q3 Report.pdf", page_number=5)])
    assert "Q3 Report.pdf" in block
    assert "page 5" in block


def test_context_block_omits_page_when_none():
    block = build_rag_context_block([_chunk(page_number=None)])
    assert "page" not in block


def test_context_block_includes_chunk_content():
    block = build_rag_context_block([_chunk(content="A very specific fact.")])
    assert "A very specific fact." in block


def test_user_prompt_includes_context_and_question():
    prompt = build_rag_user_prompt(context_block="[1] some context", question="What happened?")
    assert "[1] some context" in prompt
    assert "What happened?" in prompt
