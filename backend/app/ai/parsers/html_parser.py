from bs4 import BeautifulSoup

from app.ai.parsers.base import DocumentParser, ParsedDocument, ParsedPage


class HTMLParser(DocumentParser):
    @property
    def supported_mime_types(self) -> set[str]:
        return {"text/html"}

    def parse(self, file_bytes: bytes) -> ParsedDocument:
        soup = BeautifulSoup(file_bytes, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines()]
        cleaned = "\n".join(line for line in lines if line)
        return ParsedDocument(pages=[ParsedPage(page_number=1, text=cleaned)])
