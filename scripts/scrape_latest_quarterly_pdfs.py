"""Scrape latest quarterly-result PDFs for top 5 NIFTY 50 companies.

Run:
    python scripts/scrape_latest_quarterly_pdfs.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.nifty50_top5_config import TOP5_NIFTY50  # noqa: E402

RAW_PDF_DIR = PROJECT_ROOT / "data" / "raw_pdfs"
EARNINGS_DIR = RAW_PDF_DIR
MANIFEST_PATH = RAW_PDF_DIR / "earnings_manifest.json"
TIMEOUT = httpx.Timeout(45.0, connect=15.0)
PDF_MAGIC = b"%PDF"
MIN_PDF_BYTES = 15_000

KEYWORD_HINTS = ("quarter", "results", "financial-results", "earnings", "investor")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def _load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {"downloads": []}
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"downloads": []}


def _save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _normalized(u: str) -> str:
    return u.strip().rstrip("/")


def _is_fetchable_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False
    low = url.lower()
    return not (low.startswith("javascript:") or "void(0)" in low)


def _extract_candidate_pages(client: httpx.Client, quote_url: str) -> list[str]:
    response = client.get(quote_url, follow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    seen: set[str] = {_normalized(quote_url)}
    candidates: list[str] = [_normalized(quote_url)]

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        full = urljoin(quote_url, href)
        if not _is_fetchable_url(full):
            continue
        parsed = urlparse(full)
        if parsed.netloc and "moneycontrol.com" not in parsed.netloc:
            continue
        normalized = _normalized(full)
        text_blob = f"{anchor.get_text(' ', strip=True)} {normalized}".lower()
        if any(k in text_blob for k in KEYWORD_HINTS) and normalized not in seen:
            seen.add(normalized)
            candidates.append(normalized)
    return candidates[:20]


def _extract_pdf_links(client: httpx.Client, page_url: str) -> list[str]:
    if not _is_fetchable_url(page_url):
        return []
    try:
        response = client.get(page_url, follow_redirects=True)
        response.raise_for_status()
    except (httpx.HTTPError, ValueError):
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    found: list[str] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        full = _normalized(urljoin(page_url, href))
        if not _is_fetchable_url(full):
            continue
        low = full.lower()
        if ".pdf" in low or "pdf" in low:
            if full not in seen:
                seen.add(full)
                found.append(full)
    return found


def _guess_quarter_hint(url: str) -> str:
    low = url.lower()
    quarter = "unknown_q"
    for token in ("q1", "q2", "q3", "q4"):
        if token in low:
            quarter = token.upper()
            break

    fy_match = re.search(r"(fy[\s\-_/]?\d{2})", low)
    fy = fy_match.group(1).upper().replace(" ", "").replace("-", "").replace("_", "") if fy_match else "FYXX"
    return f"{quarter}_{fy}"


def _is_probable_pdf(content: bytes, content_type: str | None) -> bool:
    if content[:4] == PDF_MAGIC:
        return True
    if content_type and "pdf" in content_type.lower():
        return True
    return False


def _download_pdf(
    client: httpx.Client,
    symbol: str,
    url: str,
    downloaded_urls: set[str],
) -> tuple[bool, str]:
    if _normalized(url) in downloaded_urls:
        return False, "already_downloaded_url"

    try:
        response = client.get(url, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return False, f"http_error: {exc}"

    content = response.content
    if not _is_probable_pdf(content, response.headers.get("content-type")):
        return False, "not_pdf"
    if len(content) < MIN_PDF_BYTES:
        return False, f"too_small:{len(content)}"

    digest = hashlib.sha256(content).hexdigest()[:12]
    quarter_hint = _guess_quarter_hint(url)
    filename = f"earnings_{symbol.lower()}_{quarter_hint}_{digest}.pdf"
    dest = EARNINGS_DIR / filename
    if dest.exists():
        return False, "already_exists_hash"

    dest.write_bytes(content)
    return True, filename


def main() -> int:
    RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)
    EARNINGS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest()
    existing_downloads = manifest.get("downloads", [])
    downloaded_urls = {d.get("source_url", "") for d in existing_downloads}

    added = 0
    scanned_pages = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
        for company in TOP5_NIFTY50:
            symbol = company["symbol"]
            quote_url = company["moneycontrol_quote_url"]
            print(f"\n[{symbol}] scanning {quote_url}")

            try:
                pages = _extract_candidate_pages(client, quote_url)
            except httpx.HTTPError as exc:
                print(f"  failed quote fetch: {exc}")
                continue

            scanned_pages += len(pages)
            company_done = False
            for page in pages:
                if company_done:
                    break
                links = _extract_pdf_links(client, page)
                for link in links:
                    ok, detail = _download_pdf(
                        client=client,
                        symbol=symbol,
                        url=link,
                        downloaded_urls=downloaded_urls,
                    )
                    if not ok:
                        continue

                    added += 1
                    downloaded_urls.add(_normalized(link))
                    manifest.setdefault("downloads", []).append(
                        {
                            "filename": detail,
                            "symbol": symbol,
                            "company_name": company["company_name"],
                            "source_url": _normalized(link),
                            "vertical": "earnings",
                            "retrieved_at": now_iso,
                        }
                    )
                    print(f"  + downloaded {detail}")
                    company_done = True
                    break

    _save_manifest(manifest)
    print("\nRun summary")
    print(f"  scanned_pages: {scanned_pages}")
    print(f"  new_pdfs: {added}")
    print(f"  raw_pdf_dir: {EARNINGS_DIR}")
    print(f"  manifest: {MANIFEST_PATH}")
    if added == 0:
        print("No new PDFs found. You can still add URLs manually into earnings_manifest.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

