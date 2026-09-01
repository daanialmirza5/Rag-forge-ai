from functools import lru_cache

from app.ai.parsers.base import DocumentParser
from app.ai.parsers.docx_parser import DocxParser
from app.ai.parsers.html_parser import HTMLParser
from app.ai.parsers.pdf_parser import PDFParser
from app.ai.parsers.text_parser import MarkdownParser, PlainTextParser
from app.core.exceptions import ValidationAppError

SUPPORTED_MIME_TYPES: set[str] = set()


@lru_cache
def _parsers() -> tuple[DocumentParser, ...]:
    parsers: tuple[DocumentParser, ...] = (
        PDFParser(),
        DocxParser(),
        HTMLParser(),
        MarkdownParser(),
        PlainTextParser(),
    )
    for parser in parsers:
        SUPPORTED_MIME_TYPES.update(parser.supported_mime_types)
    return parsers


def get_parser_for_mime_type(mime_type: str) -> DocumentParser:
    for parser in _parsers():
        if mime_type in parser.supported_mime_types:
            return parser
    raise ValidationAppError(f"Unsupported file type: {mime_type}")


def is_supported_mime_type(mime_type: str) -> bool:
    _parsers()  # ensure SUPPORTED_MIME_TYPES is populated
    return mime_type in SUPPORTED_MIME_TYPES
