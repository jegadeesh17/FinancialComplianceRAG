"""Tests for dual-vertical corpus balance checks."""

from __future__ import annotations

import json
from pathlib import Path

from src.corpus_stats import classify_pdf_names, corpus_balance_warnings, summarize_corpus


def _write_manifest(raw: Path, downloads: list[dict]) -> None:
    (raw / "earnings_manifest.json").write_text(
        json.dumps({"downloads": downloads}),
        encoding="utf-8",
    )


def test_classify_pdf_names_by_vertical(tmp_path):
    raw = tmp_path / "raw_pdfs"
    raw.mkdir()
    (raw / "rbi_master_direction_kyc.pdf").write_bytes(b"%PDF compliance")
    (raw / "earnings_hdfcbank_q1_fy26_abcd.pdf").write_bytes(b"%PDF earnings")
    _write_manifest(
        raw,
        [
            {
                "filename": "earnings_hdfcbank_q1_fy26_abcd.pdf",
                "vertical": "earnings",
                "symbol": "HDFCBANK",
            }
        ],
    )

    compliance, earnings = classify_pdf_names(raw)
    assert compliance == ["rbi_master_direction_kyc.pdf"]
    assert earnings == ["earnings_hdfcbank_q1_fy26_abcd.pdf"]


def test_corpus_balance_warnings_when_earnings_low(tmp_path):
    raw = tmp_path / "raw_pdfs"
    raw.mkdir()
    for i in range(5):
        (raw / f"compliance_{i}.pdf").write_bytes(b"%PDF")
    _write_manifest(raw, [])

    warnings = corpus_balance_warnings(
        raw,
        min_earnings_pdfs=3,
        min_compliance_pdfs=2,
        target_earnings_ratio_low=0.2,
        target_earnings_ratio_high=0.8,
    )
    assert any("earnings PDFs below target" in w for w in warnings)
    assert any("earnings ratio outside target" in w for w in warnings)


def test_corpus_balance_no_warnings_when_balanced(tmp_path):
    raw = tmp_path / "raw_pdfs"
    raw.mkdir()
    (raw / "rbi.pdf").write_bytes(b"%PDF")
    (raw / "sebi.pdf").write_bytes(b"%PDF")
    (raw / "earnings_hdfcbank_q1.pdf").write_bytes(b"%PDF")
    (raw / "earnings_reliance_q1.pdf").write_bytes(b"%PDF")
    _write_manifest(
        raw,
        [
            {"filename": "earnings_hdfcbank_q1.pdf", "vertical": "earnings"},
            {"filename": "earnings_reliance_q1.pdf", "vertical": "earnings"},
        ],
    )

    stats = summarize_corpus(raw)
    assert stats["vertical_counts"]["compliance"] == 2
    assert stats["vertical_counts"]["earnings"] == 2
    warnings = corpus_balance_warnings(
        raw,
        min_earnings_pdfs=2,
        min_compliance_pdfs=2,
        target_earnings_ratio_low=0.4,
        target_earnings_ratio_high=0.6,
    )
    assert warnings == []
