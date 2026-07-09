"""Create a lightweight market sentiment + fundamentals snapshot from Moneycontrol.

Run:
    python scripts/scrape_market_sentiment.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.nifty50_top5_config import TOP5_NIFTY50  # noqa: E402

OUTPUT_DIR = PROJECT_ROOT / "data" / "market_signals"
OUTPUT_FILE = OUTPUT_DIR / "moneycontrol_top5_snapshot.json"
TIMEOUT = httpx.Timeout(35.0, connect=15.0)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

POSITIVE_WORDS = {
    "beat",
    "growth",
    "up",
    "strong",
    "gain",
    "rally",
    "upgrade",
    "profit",
    "record",
}
NEGATIVE_WORDS = {
    "miss",
    "down",
    "weak",
    "fall",
    "drop",
    "cut",
    "downgrade",
    "loss",
    "decline",
}


def _clean_numeric(text: str) -> float | None:
    stripped = text.replace(",", "").replace("%", "").strip()
    match = re.search(r"[-+]?\d+(\.\d+)?", stripped)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _fetch_html(client: httpx.Client, url: str) -> str:
    response = client.get(url, follow_redirects=True)
    response.raise_for_status()
    return response.text


def _extract_fundamentals(soup: BeautifulSoup) -> dict[str, float | None]:
    text = soup.get_text(" ", strip=True).lower()

    def find_value(keyword: str) -> float | None:
        idx = text.find(keyword)
        if idx < 0:
            return None
        window = text[idx : idx + 120]
        return _clean_numeric(window)

    return {
        "pe_ratio": find_value("p/e"),
        "market_cap": find_value("mcap"),
        "book_value": find_value("book value"),
        "dividend_yield": find_value("div yield"),
    }


def _extract_headlines(soup: BeautifulSoup, base_url: str, limit: int = 15) -> list[dict[str, str]]:
    headlines: list[dict[str, str]] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        title = anchor.get_text(" ", strip=True)
        if len(title) < 20:
            continue
        href = urljoin(base_url, anchor["href"])
        low = f"{title} {href}".lower()
        if "news" not in low and "result" not in low and "quarter" not in low:
            continue
        if title in seen:
            continue
        seen.add(title)
        headlines.append({"title": title, "url": href})
        if len(headlines) >= limit:
            break
    return headlines


def _headline_sentiment(headlines: list[dict[str, str]]) -> dict[str, object]:
    score = 0
    token_counter: Counter[str] = Counter()
    for item in headlines:
        tokens = re.findall(r"[a-zA-Z]+", item["title"].lower())
        token_counter.update(tokens)
        score += sum(1 for t in tokens if t in POSITIVE_WORDS)
        score -= sum(1 for t in tokens if t in NEGATIVE_WORDS)

    label = "neutral"
    if score > 2:
        label = "positive"
    elif score < -2:
        label = "negative"

    return {
        "label": label,
        "score": score,
        "top_tokens": [w for w, _ in token_counter.most_common(10)],
    }


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    as_of = datetime.now(timezone.utc).isoformat()
    snapshot: dict[str, object] = {
        "source": "moneycontrol",
        "as_of": as_of,
        "companies": [],
    }

    with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
        for company in TOP5_NIFTY50:
            symbol = company["symbol"]
            quote_url = company["moneycontrol_quote_url"]
            print(f"[{symbol}] scraping market snapshot")
            try:
                html = _fetch_html(client, quote_url)
            except httpx.HTTPError as exc:
                print(f"  failed: {exc}")
                snapshot["companies"].append(
                    {
                        "symbol": symbol,
                        "company_name": company["company_name"],
                        "quote_url": quote_url,
                        "error": str(exc),
                    }
                )
                continue

            soup = BeautifulSoup(html, "html.parser")
            headlines = _extract_headlines(soup, quote_url, limit=12)
            sentiment = _headline_sentiment(headlines)
            fundamentals = _extract_fundamentals(soup)
            snapshot["companies"].append(
                {
                    "symbol": symbol,
                    "company_name": company["company_name"],
                    "quote_url": quote_url,
                    "fundamentals": fundamentals,
                    "sentiment": sentiment,
                    "headline_count": len(headlines),
                    "headlines": headlines,
                }
            )

    OUTPUT_FILE.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"\nSaved snapshot: {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

