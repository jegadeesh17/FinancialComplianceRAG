"""Rebuild index and validate corpus balance across compliance + earnings verticals.

Run:
    python scripts/refresh_dual_vertical_index.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_settings  # noqa: E402
from src.corpus_stats import classify_pdf_names, corpus_balance_warnings  # noqa: E402
from src.vectorstore import build_vector_index, get_collection_count  # noqa: E402

MANIFEST_PATH = PROJECT_ROOT / "data" / "raw_pdfs" / "earnings_manifest.json"


def main() -> int:
    settings = get_settings()
    pdf_dir = settings.raw_pdf_path
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs in {pdf_dir}.")
        return 1

    compliance_names, earnings_names = classify_pdf_names(pdf_dir)
    total = len(pdfs)
    earnings_ratio = len(earnings_names) / total if total else 0.0

    print("Corpus mix")
    print(f"  total_pdfs: {total}")
    print(f"  compliance_pdfs: {len(compliance_names)}")
    print(f"  earnings_pdfs: {len(earnings_names)}")
    print(f"  earnings_ratio: {earnings_ratio:.2f}")

    warnings = corpus_balance_warnings(pdf_dir)

    if warnings:
        print("\nBalance warnings:")
        for item in warnings:
            print(f"  - {item}")
        print("Recommendation: run quarterly scrapers or add compliance PDFs before next demo.")

    print("\nRebuilding vector index ...")
    stored = build_vector_index(pdf_dir=pdf_dir, settings=settings)
    count = get_collection_count(settings=settings)
    print(f"Stored chunks in last run: {stored}")
    print(f"Collection count: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

