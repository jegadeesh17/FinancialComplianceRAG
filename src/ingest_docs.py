"""PDF ingestion: text extraction and paragraph-aware chunking."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import fitz

from src.config import Settings, get_settings
from src.schemas import DocumentChunk

_PARAGRAPH_BREAK = re.compile(r"\n\s*\n+")


def _load_earnings_manifest(pdf_dir: Path) -> dict[str, dict]:
    manifest_path = pdf_dir / "earnings_manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: dict[str, dict] = {}
    for item in payload.get("downloads", []):
        name = str(item.get("filename", "")).strip()
        if name:
            out[name] = item
    return out


def _infer_regulator(filename: str) -> str:
    lower = filename.lower()
    if "rbi" in lower:
        return "RBI"
    if "sebi" in lower:
        return "SEBI"
    return "other"


def _source_metadata_for_file(source: str, manifest_map: dict[str, dict]) -> dict[str, str]:
    row = manifest_map.get(source, {})
    is_earnings = source.startswith("earnings_") or row.get("vertical") == "earnings"
    return {
        "source_url": str(row.get("source_url", "")),
        "retrieved_at": str(
            row.get("retrieved_at", datetime.now(timezone.utc).isoformat())
        ),
        "regulator": str(row.get("regulator", _infer_regulator(source))),
        "company": str(row.get("symbol", row.get("company_name", ""))),
        "document_vertical": "earnings" if is_earnings else "compliance",
    }


def extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    """Extract non-empty text per page. Returns (1-indexed page, text) pairs."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    pages: list[tuple[int, str]] = []
    with fitz.open(path) as doc:
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append((page_num, text))
    return pages


def _split_long_block(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split oversized text when a single paragraph exceeds chunk_size."""
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - chunk_overlap, start + 1)
    return [c for c in chunks if c]


def _paragraphs_from_text(text: str) -> list[str]:
    parts = _PARAGRAPH_BREAK.split(text)
    return [p.strip() for p in parts if p.strip()]


def chunk_page_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> list[str]:
    """
    Chunk page text paragraph-aware: prefer paragraph boundaries over hard splits.
    Applies overlap by prefixing tail of the previous chunk when starting a new one.
    """
    if not text.strip():
        return []

    paragraphs = _paragraphs_from_text(text)
    if not paragraphs:
        return _split_long_block(text, chunk_size, chunk_overlap)

    raw_chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(para) > chunk_size:
            if current:
                raw_chunks.append(current)
                current = ""
            raw_chunks.extend(_split_long_block(para, chunk_size, chunk_overlap))
            continue

        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                raw_chunks.append(current)
            current = para

    if current:
        raw_chunks.append(current)

    if not raw_chunks:
        return []

    if chunk_overlap <= 0 or len(raw_chunks) == 1:
        return raw_chunks

    overlapped: list[str] = [raw_chunks[0]]
    for chunk in raw_chunks[1:]:
        prev = overlapped[-1]
        tail = prev[-chunk_overlap:] if len(prev) > chunk_overlap else prev
        merged = f"{tail}\n\n{chunk}".strip()
        if len(merged) <= chunk_size:
            overlapped.append(merged)
        else:
            overlapped.append(chunk)
    return overlapped


def ingest_pdf(
    pdf_path: Path,
    settings: Settings | None = None,
    source_metadata: dict[str, str] | None = None,
) -> list[DocumentChunk]:
    """Extract and chunk a single PDF into DocumentChunk records."""
    settings = settings or get_settings()
    source = Path(pdf_path).name
    pages = extract_pages(pdf_path)
    source_metadata = source_metadata or {}

    chunks: list[DocumentChunk] = []
    chunk_index = 0
    for page_num, page_text in pages:
        for text in chunk_page_text(
            page_text,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        ):
            chunks.append(
                DocumentChunk(
                    source=source,
                    page=page_num,
                    text=text,
                    chunk_index=chunk_index,
                    source_url=source_metadata.get("source_url", ""),
                    retrieved_at=source_metadata.get("retrieved_at", ""),
                    regulator=source_metadata.get("regulator", "other"),
                    company=source_metadata.get("company", ""),
                    document_vertical=source_metadata.get("document_vertical", "compliance"),
                )
            )
            chunk_index += 1
    return chunks


def ingest_directory(
    directory: Path | None = None,
    settings: Settings | None = None,
) -> list[DocumentChunk]:
    """Ingest all PDF files in a directory (sorted by filename)."""
    settings = settings or get_settings()
    pdf_dir = directory or settings.raw_pdf_path
    pdf_dir = Path(pdf_dir)
    if not pdf_dir.exists():
        raise FileNotFoundError(f"PDF directory not found: {pdf_dir}")
    manifest_map = _load_earnings_manifest(pdf_dir)

    all_chunks: list[DocumentChunk] = []
    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        metadata = _source_metadata_for_file(pdf_path.name, manifest_map)
        all_chunks.extend(ingest_pdf(pdf_path, settings=settings, source_metadata=metadata))
    return all_chunks
