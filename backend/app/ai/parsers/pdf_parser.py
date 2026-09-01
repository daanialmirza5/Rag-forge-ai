"""PDF parser with an OCR fallback for scanned/image-only pages.

`pdfplumber` extracts embedded text directly (fast, accurate) for normal
PDFs. A page with no meaningfully-extractable text is assumed to be a
scanned image and is rasterized (`pdf2image`, requires the system `poppler`
binary) then OCR'd (`pytesseract`, requires the system `tesseract` binary).
Both binaries are installed in the production Docker image (see
`docs/PROGRESS.md`); if either is missing (e.g. local dev without them), OCR
for that page is skipped with a logged warning rather than failing the whole
document — partial extraction beats none.
"""

import io

import pdfplumber

from app.ai.parsers.base import DocumentParser, ParsedDocument, ParsedPage
from app.core.logging import get_logger

logger = get_logger(__name__)

_MIN_CHARS_BEFORE_OCR_FALLBACK = 10


def _ocr_page(file_bytes: bytes, page_number: int) -> str:
    try:
        import pytesseract
        from pdf2image import convert_from_bytes
    except ImportError:
        logger.warning("ocr_dependencies_missing", page=page_number)
        return ""

    try:
        images = convert_from_bytes(
            file_bytes, first_page=page_number, last_page=page_number, dpi=300
        )
        if not images:
            return ""
        return pytesseract.image_to_string(images[0])
    except Exception as exc:  # noqa: BLE001 — OCR is best-effort, never fatal
        logger.warning("ocr_page_failed", page=page_number, error=str(exc))
        return ""


class PDFParser(DocumentParser):
    @property
    def supported_mime_types(self) -> set[str]:
        return {"application/pdf"}

    def parse(self, file_bytes: bytes) -> ParsedDocument:
        pages: list[ParsedPage] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = (page.extract_text() or "").strip()
                if len(text) < _MIN_CHARS_BEFORE_OCR_FALLBACK:
                    ocr_text = _ocr_page(file_bytes, i).strip()
                    if ocr_text:
                        text = ocr_text
                pages.append(ParsedPage(page_number=i, text=text))

        return ParsedDocument(pages=pages)
