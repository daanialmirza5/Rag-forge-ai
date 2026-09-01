import markdown as markdown_lib
from bs4 import BeautifulSoup

from app.ai.parsers.base import DocumentParser, ParsedDocument, ParsedPage


class PlainTextParser(DocumentParser):
    @property
    def supported_mime_types(self) -> set[str]:
        return {"text/plain"}

    def parse(self, file_bytes: bytes) -> ParsedDocument:
        text = file_bytes.decode("utf-8", errors="replace")
        return ParsedDocument(pages=[ParsedPage(page_number=1, text=text)])


class MarkdownParser(DocumentParser):
    """Renders Markdown to HTML then strips tags — keeps prose readable for
    embedding/generation without carrying Markdown syntax noise (`#`, `**`,
    link syntax) into chunk text."""

    @property
    def supported_mime_types(self) -> set[str]:
        return {"text/markdown", "text/x-markdown"}

    def parse(self, file_bytes: bytes) -> ParsedDocument:
        raw = file_bytes.decode("utf-8", errors="replace")
        html = markdown_lib.markdown(raw, extensions=["tables", "fenced_code"])
        text = BeautifulSoup(html, "html.parser").get_text(separator="\n")
        return ParsedDocument(pages=[ParsedPage(page_number=1, text=text)])
