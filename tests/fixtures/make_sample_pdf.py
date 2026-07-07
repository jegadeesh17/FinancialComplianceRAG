"""Create a minimal text PDF for unit tests."""

from pathlib import Path

import fitz


def write_sample_pdf(path: Path) -> Path:
    """Write a small multi-page compliance-style PDF for ingestion tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    pages = [
        (
            "RBI Master Direction — Know Your Customer (KYC)\n\n"
            "Banks shall obtain official identification documents for individual customers. "
            "The minimum KYC requirements include proof of identity and proof of address."
        ),
        (
            "Section 4 — Capital Adequacy\n\n"
            "Scheduled commercial banks must maintain a minimum capital adequacy ratio. "
            "The minimum capital requirement is prescribed under applicable RBI norms."
        ),
        (
            "HDFC Bank — Annual Report Excerpt\n\n"
            "Net interest income for the financial year was reported in the annual disclosure. "
            "Total deposits increased year over year per the audited financial statements."
        ),
    ]
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text, fontsize=11)
    doc.save(path)
    doc.close()
    return path
