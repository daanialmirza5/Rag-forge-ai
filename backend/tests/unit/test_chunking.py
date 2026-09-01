from app.ai.chunking.recursive_chunker import RecursiveChunker
from app.ai.parsers.base import ParsedDocument, ParsedPage


def test_short_page_produces_single_chunk():
    document = ParsedDocument(pages=[ParsedPage(page_number=1, text="Short bit of text.")])
    chunks = RecursiveChunker(chunk_size=1000, chunk_overlap=100).chunk(document)
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].page_number == 1
    assert chunks[0].token_count >= 1


def test_long_page_splits_into_overlapping_chunks():
    paragraph = "This is a sentence that repeats to build up a long document. "
    long_text = paragraph * 100  # ~6400 chars
    document = ParsedDocument(pages=[ParsedPage(page_number=1, text=long_text)])

    chunks = RecursiveChunker(chunk_size=500, chunk_overlap=50).chunk(document)

    assert len(chunks) > 1
    # chunk_index is sequential starting at 0
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    # every chunk stays close to the requested size (allow slack for the
    # splitter preferring sentence boundaries over a hard cutoff)
    assert all(len(c.content) <= 500 + 200 for c in chunks)
    # consecutive chunks share an overlapping tail/head substring
    assert chunks[0].content[-20:] in chunks[1].content


def test_page_numbers_preserved_across_pages():
    document = ParsedDocument(
        pages=[
            ParsedPage(page_number=1, text="Page one content."),
            ParsedPage(page_number=2, text="Page two content."),
        ]
    )
    chunks = RecursiveChunker(chunk_size=1000, chunk_overlap=0).chunk(document)
    assert [c.page_number for c in chunks] == [1, 2]
    # chunk_index keeps incrementing across the page boundary, not resetting
    assert [c.chunk_index for c in chunks] == [0, 1]


def test_blank_pages_are_skipped():
    document = ParsedDocument(
        pages=[
            ParsedPage(page_number=1, text="   \n  "),
            ParsedPage(page_number=2, text="Real content here."),
        ]
    )
    chunks = RecursiveChunker(chunk_size=1000, chunk_overlap=0).chunk(document)
    assert len(chunks) == 1
    assert chunks[0].page_number == 2


def test_empty_document_produces_no_chunks():
    document = ParsedDocument(pages=[])
    assert RecursiveChunker().chunk(document) == []
