"""Corpus-level summary utilities for dual-vertical visibility."""

from __future__ import annotations

import json
from pathlib import Path


def _load_manifest(raw_pdf_dir: Path) -> dict:
    manifest_path = raw_pdf_dir / "earnings_manifest.json"
    if not manifest_path.exists():
        return {"downloads": []}
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {"downloads": []}


def summarize_corpus(raw_pdf_dir: Path) -> dict:
    """Return corpus mix stats across compliance and earnings documents."""
    pdfs = sorted(raw_pdf_dir.glob("*.pdf"))
    manifest = _load_manifest(raw_pdf_dir)
    manifest_map = {str(d.get("filename", "")): d for d in manifest.get("downloads", [])}

    vertical_counts = {"compliance": 0, "earnings": 0}
    regulator_counts: dict[str, int] = {}
    company_counts: dict[str, int] = {}

    for pdf in pdfs:
        row = manifest_map.get(pdf.name, {})
        is_earnings = pdf.name.startswith("earnings_") or row.get("vertical") == "earnings"
        vertical = "earnings" if is_earnings else "compliance"
        vertical_counts[vertical] = vertical_counts.get(vertical, 0) + 1

        regulator = str(row.get("regulator", "other"))
        low = pdf.name.lower()
        if regulator == "other":
            if "rbi" in low:
                regulator = "RBI"
            elif "sebi" in low:
                regulator = "SEBI"
        regulator_counts[regulator] = regulator_counts.get(regulator, 0) + 1

        company = str(row.get("symbol", row.get("company_name", ""))).strip()
        if company:
            company_counts[company] = company_counts.get(company, 0) + 1

    total = len(pdfs)
    earnings_ratio = (vertical_counts.get("earnings", 0) / total) if total else 0.0
    return {
        "total_pdfs": total,
        "vertical_counts": vertical_counts,
        "regulator_counts": regulator_counts,
        "company_counts": company_counts,
        "earnings_ratio": round(earnings_ratio, 3),
    }


def classify_pdf_names(raw_pdf_dir: Path) -> tuple[list[str], list[str]]:
    """Return (compliance_filenames, earnings_filenames) from raw PDF directory."""
    manifest = _load_manifest(raw_pdf_dir)
    manifest_map = {str(d.get("filename", "")): d for d in manifest.get("downloads", [])}
    compliance: list[str] = []
    earnings: list[str] = []
    for pdf in sorted(raw_pdf_dir.glob("*.pdf")):
        row = manifest_map.get(pdf.name, {})
        is_earnings = pdf.name.startswith("earnings_") or row.get("vertical") == "earnings"
        if is_earnings:
            earnings.append(pdf.name)
        else:
            compliance.append(pdf.name)
    return compliance, earnings


def corpus_balance_warnings(
    raw_pdf_dir: Path,
    *,
    min_earnings_pdfs: int = 10,
    min_compliance_pdfs: int = 5,
    target_earnings_ratio_low: float = 0.45,
    target_earnings_ratio_high: float = 0.70,
) -> list[str]:
    """Return warning messages when corpus mix is below demo targets."""
    stats = summarize_corpus(raw_pdf_dir)
    warnings: list[str] = []
    earnings_count = stats["vertical_counts"].get("earnings", 0)
    compliance_count = stats["vertical_counts"].get("compliance", 0)
    ratio = stats.get("earnings_ratio", 0.0)

    if earnings_count < min_earnings_pdfs:
        warnings.append(f"earnings PDFs below target ({earnings_count} < {min_earnings_pdfs})")
    if compliance_count < min_compliance_pdfs:
        warnings.append(f"compliance PDFs below target ({compliance_count} < {min_compliance_pdfs})")
    if ratio < target_earnings_ratio_low or ratio > target_earnings_ratio_high:
        warnings.append(
            "earnings ratio outside target "
            f"[{target_earnings_ratio_low:.2f}, {target_earnings_ratio_high:.2f}]"
        )
    return warnings

