from __future__ import annotations

import hashlib
import re
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from .models import PolicyDocument, SourceChunk

MAX_FILE_BYTES = 20 * 1024 * 1024
CHUNK_CHARS = 1100
HEADING_RE = re.compile(r"^\s*(?:#{1,6}\s+|(?:\d+(?:\.\d+)*[.)]?\s+))(.{2,100})\s*$")


def _split_long(text: str, limit: int = CHUNK_CHARS) -> list[str]:
    remaining = text.strip()
    pieces: list[str] = []
    while len(remaining) > limit:
        cut = remaining.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        pieces.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        pieces.append(remaining)
    return pieces


def _chunks_from_text(
    text: str,
    *,
    source_start: int,
    page: int | None = None,
    initial_section: str = "Document",
) -> tuple[list[SourceChunk], int]:
    chunks: list[SourceChunk] = []
    section = initial_section
    paragraph_lines: list[str] = []
    next_id = source_start

    def flush() -> None:
        nonlocal next_id, paragraph_lines
        paragraph = "\n".join(line.strip() for line in paragraph_lines).strip()
        paragraph_lines = []
        if not paragraph:
            return
        for piece in _split_long(paragraph):
            chunks.append(
                SourceChunk(
                    source_id=f"S{next_id:04d}",
                    text=piece,
                    section=section,
                    page=page,
                )
            )
            next_id += 1

    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            flush()
            section = match.group(1).strip()
        elif not line.strip():
            flush()
        else:
            paragraph_lines.append(line)
    flush()
    return chunks, next_id


def _read_docx(path: Path) -> str:
    document = Document(str(path))
    blocks: list[str] = []
    for paragraph in document.paragraphs:
        value = paragraph.text.strip()
        if value:
            blocks.append(value)
    for table_index, table in enumerate(document.tables, start=1):
        blocks.append(f"Table {table_index}")
        for row in table.rows:
            cells = [cell.text.strip().replace("\n", " / ") for cell in row.cells]
            if any(cells):
                blocks.append(" | ".join(cells))
    return "\n\n".join(blocks)


def read_policy(path: str | Path) -> PolicyDocument:
    source = Path(path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"Policy file not found: {source}")
    raw = source.read_bytes()
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("Policy exceeds the 20 MB local processing limit.")
    extension = source.suffix.lower()
    chunks: list[SourceChunk] = []

    if extension in {".txt", ".md"}:
        extracted = raw.decode("utf-8-sig", errors="replace")
        chunks, _ = _chunks_from_text(extracted, source_start=1)
    elif extension == ".docx":
        extracted = _read_docx(source)
        chunks, _ = _chunks_from_text(extracted, source_start=1)
    elif extension == ".pdf":
        try:
            reader = PdfReader(str(source))
            page_texts = [(index + 1, page.extract_text() or "") for index, page in enumerate(reader.pages)]
        except Exception as exc:
            raise ValueError(f"Could not read this PDF: {exc}") from exc
        for page_number, page_text in page_texts:
            page_chunks, _ = _chunks_from_text(
                page_text,
                source_start=len(chunks) + 1,
                page=page_number,
                initial_section=f"PDF page {page_number}",
            )
            chunks.extend(page_chunks)
        extracted = "\n\n".join(
            f"[PDF page {page_number}]\n{page_text.strip()}"
            for page_number, page_text in page_texts
            if page_text.strip()
        )
        if not extracted.strip():
            raise ValueError(
                "This PDF has no extractable text. It may be scanned; add OCR before auditing it."
            )
    else:
        raise ValueError("Supported policy formats are .pdf, .docx, .txt, and .md.")

    if not extracted.strip():
        raise ValueError("The policy contains no readable text.")
    if not chunks:
        raise ValueError("The policy text could not be split into evidence passages.")

    return PolicyDocument(
        path=str(source.resolve()),
        extracted_text=extracted,
        chunks=chunks,
        sha256=hashlib.sha256(raw).hexdigest(),
    )
