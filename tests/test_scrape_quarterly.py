"""Tests for quarterly scrape helpers (mocked HTTP)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import httpx

from scripts.scrape_latest_quarterly_pdfs import (
    _download_pdf,
    _extract_pdf_links,
    _is_fetchable_url,
    _is_probable_pdf,
    _normalized,
)


class _FakeResponse:
    def __init__(self, content: bytes, content_type: str | None = None, status_code: int = 200):
        self.content = content
        self.text = content.decode("utf-8", errors="ignore")
        self.headers = {"content-type": content_type} if content_type else {}
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("http error")


def test_extract_pdf_links_from_html():
    client = MagicMock()
    client.get.return_value = _FakeResponse(
        b'<html><a href="/files/q1-results.pdf">Q1</a></html>',
        content_type="text/html",
    )
    links = _extract_pdf_links(client, "https://www.moneycontrol.com/example")
    assert links == ["https://www.moneycontrol.com/files/q1-results.pdf"]


def test_extract_pdf_links_handles_http_error():
    client = MagicMock()
    client.get.side_effect = httpx.HTTPError("network")
    assert _extract_pdf_links(client, "https://www.moneycontrol.com/broken") == []


def test_extract_pdf_links_skips_void_urls():
    client = MagicMock()
    assert _extract_pdf_links(client, "/void(0)") == []
    client.get.assert_not_called()
    assert _is_fetchable_url("javascript:void(0)") is False


def test_is_probable_pdf_magic_bytes():
    assert _is_probable_pdf(b"%PDF-1.4 content", "application/octet-stream") is True
    assert _is_probable_pdf(b"<html>", "text/html") is False


def test_download_pdf_skips_duplicate_url(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.scrape_latest_quarterly_pdfs.EARNINGS_DIR", tmp_path)
    client = MagicMock()
    url = "https://example.com/results/q1.pdf"
    downloaded = {_normalized(url)}

    ok, detail = _download_pdf(client, "HDFCBANK", url, downloaded)
    assert ok is False
    assert detail == "already_downloaded_url"
    client.get.assert_not_called()


def test_download_pdf_saves_valid_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.scrape_latest_quarterly_pdfs.EARNINGS_DIR", tmp_path)
    client = MagicMock()
    pdf_bytes = b"%PDF-1.4 " + (b"x" * 20_000)
    client.get.return_value = _FakeResponse(pdf_bytes, content_type="application/pdf")

    ok, filename = _download_pdf(
        client,
        "HDFCBANK",
        "https://example.com/results/q1_fy26.pdf",
        set(),
    )
    assert ok is True
    assert filename.startswith("earnings_hdfcbank_")
    assert (tmp_path / filename).exists()
