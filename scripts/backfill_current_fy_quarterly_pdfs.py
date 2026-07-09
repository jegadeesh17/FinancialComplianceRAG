"""Backfill current financial-year quarterly PDFs for top 5 NIFTY 50 companies.

Run:
    python scripts/backfill_current_fy_quarterly_pdfs.py
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
PER_COMPANY_TARGET = 3

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
KEYWORD_HINTS = ("quarter", "results", "financial-results", "earnings", "investor")


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


def _current_financial_year_tokens(now: datetime | None = None) -> set[str]:
    now = now or datetime.now(timezone.utc)
    year = now.year
    if now.month >= 4:
        start_year = year
        end_year = year + 1
    else:
        start_year = year - 1
        end_year = year
    fy_short = str(end_year)[-2:]
    return {
        f"fy{fy_short}",
        f"fy {fy_short}",
        f"{start_year}-{str(end_year)[-2:]}",
        f"{start_year}_{str(end_year)[-2:]}",
        str(start_year),
        str(end_year),
    }


def _extract_candidate_pages(client: httpx.Client, quote_url: str) -> list[str]:
    response = client.get(quote_url, follow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    candidates: list[str] = [_normalized(quote_url)]
    seen = {candidates[0]}
    for anchor in soup.find_all("a", href=True):
        full = _normalized(urljoin(quote_url, anchor["href"]))
        if not _is_fetchable_url(full):
            continue
        parsed = urlparse(full)
        if parsed.netloc and "moneycontrol.com" not in parsed.netloc:
            continue
        text_blob = f"{anchor.get_text(' ', strip=True)} {full}".lower()
        if any(k in text_blob for k in KEYWORD_HINTS) and full not in seen:
            seen.add(full)
            candidates.append(full)
    return candidates[:30]


def _extract_pdf_links(client: httpx.Client, page_url: str) -> list[str]:
    if not _is_fetchable_url(page_url):
        return []
    try:
        response = client.get(page_url, follow_redirects=True)
        response.raise_for_status()
    except (httpx.HTTPError, ValueError):
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    links: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        full = _normalized(urljoin(page_url, anchor["href"]))
        if not _is_fetchable_url(full):
            continue
        if "pdf" not in full.lower():
            continue
        if full in seen:
            continue
        seen.add(full)
        links.append(full)
    return links


def _is_current_fy_link(url: str, fy_tokens: set[str]) -> bool:
    low = url.lower()
    if any(q in low for q in ("q1", "q2", "q3", "q4")) and any(t in low for t in fy_tokens):
        return True
    return any(t in low for t in fy_tokens) and "result" in low


def _guess_quarter_hint(url: str, fy_tokens: set[str]) -> str:
    low = url.lower()
    quarter = "QX"
    for q in ("q1", "q2", "q3", "q4"):
        if q in low:
            quarter = q.upper()
            break
    fy = next((t for t in fy_tokens if t.startswith("fy")), "FYXX").replace(" ", "").upper()
    return f"{quarter}_{fy}"


def _is_probable_pdf(content: bytes, content_type: str | None) -> bool:
    if content[:4] == PDF_MAGIC:
        return True
    return bool(content_type and "pdf" in content_type.lower())


def main() -> int:
    RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)
    EARNINGS_DIR.mkdir(parents=True, exist_ok=True)
    fy_tokens = _current_financial_year_tokens()
    manifest = _load_manifest()
    downloads = manifest.get("downloads", [])
    existing_urls = {d.get("source_url", "") for d in downloads}
    now_iso = datetime.now(timezone.utc).isoformat()

    added_total = 0
    with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
        for company in TOP5_NIFTY50:
            symbol = company["symbol"]
            existing_for_symbol = [
                d for d in downloads if d.get("symbol") == symbol and d.get("vertical") == "earnings"
            ]
            if len(existing_for_symbol) >= PER_COMPANY_TARGET:
                print(f"[{symbol}] already has {len(existing_for_symbol)} PDFs (target={PER_COMPANY_TARGET})")
                continue

            print(f"\n[{symbol}] backfill scan started")
            try:
                pages = _extract_candidate_pages(client, company["moneycontrol_quote_url"])
            except httpx.HTTPError as exc:
                print(f"  quote fetch failed: {exc}")
                continue

            added_for_symbol = 0
            for page in pages:
                if len(existing_for_symbol) + added_for_symbol >= PER_COMPANY_TARGET:
                    break
                for link in _extract_pdf_links(client, page):
                    if link in existing_urls or not _is_current_fy_link(link, fy_tokens):
                        continue
                    try:
                        response = client.get(link, follow_redirects=True)
                        response.raise_for_status()
                    except httpx.HTTPError:
                        continue
                    content = response.content
                    if not _is_probable_pdf(content, response.headers.get("content-type")):
                        continue
                    if len(content) < MIN_PDF_BYTES:
                        continue

                    digest = hashlib.sha256(content).hexdigest()[:12]
                    quarter_hint = _guess_quarter_hint(link, fy_tokens)
                    filename = f"earnings_{symbol.lower()}_{quarter_hint}_{digest}.pdf"
                    dest = EARNINGS_DIR / filename
                    if dest.exists():
                        continue
                    dest.write_bytes(content)

                    entry = {
                        "filename": filename,
                        "symbol": symbol,
                        "company_name": company["company_name"],
                        "source_url": link,
                        "vertical": "earnings",
                        "retrieved_at": now_iso,
                        "financial_year_tokens": sorted(fy_tokens),
                    }
                    downloads.append(entry)
                    existing_urls.add(link)
                    added_for_symbol += 1
                    added_total += 1
                    print(f"  + {filename}")

            if added_for_symbol == 0:
                print("  no current FY PDFs discovered from scrape links.")

    manifest["downloads"] = downloads
    _save_manifest(manifest)

    print("\nBackfill summary")
    print(f"  financial_year_tokens: {sorted(fy_tokens)}")
    print(f"  new_pdfs: {added_total}")
    for company in TOP5_NIFTY50:
        symbol = company["symbol"]
        count = sum(1 for d in downloads if d.get("symbol") == symbol and d.get("vertical") == "earnings")
        status = "OK" if count >= PER_COMPANY_TARGET else "LOW"
        print(f"  {symbol}: {count} PDFs ({status})")
    print(f"  manifest: {MANIFEST_PATH}")
    print(
        "If counts are LOW, add source PDF URLs manually in earnings_manifest.json "
        "and place files in data/raw_pdfs/."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

