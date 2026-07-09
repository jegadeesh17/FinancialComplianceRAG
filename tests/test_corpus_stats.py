"""Tests for corpus mix summary utilities."""

from __future__ import annotations

import json

from src.corpus_stats import summarize_corpus


def test_summarize_corpus_vertical_counts(tmp_path):
    raw = tmp_path / "raw_pdfs"
    raw.mkdir()

    (raw / "rbi_master_direction_kyc.pdf").write_bytes(b"%PDF-1.4 compliance")
    (raw / "earnings_hdfcbank_q1_fy26_abcd1234.pdf").write_bytes(b"%PDF-1.4 earnings")

    manifest = {
        "downloads": [
            {
                "filename": "earnings_hdfcbank_q1_fy26_abcd1234.pdf",
                "symbol": "HDFCBANK",
                "company_name": "HDFC Bank Ltd",
                "source_url": "https://example.com/hdfc_q1.pdf",
                "vertical": "earnings",
                "retrieved_at": "2026-07-09T00:00:00Z",
            }
        ]
    }
    (raw / "earnings_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    stats = summarize_corpus(raw)
    assert stats["total_pdfs"] == 2
    assert stats["vertical_counts"]["compliance"] == 1
    assert stats["vertical_counts"]["earnings"] == 1
    assert stats["company_counts"]["HDFCBANK"] == 1
    assert 0.4 <= stats["earnings_ratio"] <= 0.6


def test_summarize_corpus_handles_missing_manifest(tmp_path):
    raw = tmp_path / "raw_pdfs"
    raw.mkdir()
    (raw / "sebi_circular_disclosure.pdf").write_bytes(b"%PDF-1.4 compliance")

    stats = summarize_corpus(raw)
    assert stats["total_pdfs"] == 1
    assert stats["vertical_counts"]["compliance"] == 1
    assert stats["vertical_counts"]["earnings"] == 0
    assert "SEBI" in stats["regulator_counts"]

