# PDF Data Sources — Financial Compliance RAG

This document lists the **initial 3 PDFs** and how to obtain them. PDFs are stored in `data/raw_pdfs/` (gitignored).

---

## Initial corpus (Phase 2)

| # | Type | Document | Where to get it | Filename suggestion |
|---|------|----------|-----------------|---------------------|
| 1 | **Regulatory** | RBI Master Direction on KYC | [RBI Master Directions](https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx) → search "KYC" | `rbi_master_direction_kyc.pdf` |
| 2 | **Annual report** | HDFC Bank Annual Report (FY2023–24 or latest) | [HDFC Bank Investor Relations](https://www.hdfcbank.com/personal/about-us/investor-relations/financial-results) → Annual Report PDF | `hdfc_bank_annual_report.pdf` |
| 3 | **Regulatory** | SEBI circular (e.g. LODR / disclosure) | [SEBI Legal Framework](https://www.sebi.gov.in/legal.html) → Circulars | `sebi_circular_disclosure.pdf` |

---

## Do you have to find them manually?

**Phase 2:** We will add `scripts/download_docs.py` with **direct PDF URLs** where stable. For RBI/SEBI/HDFC, sites sometimes change links — you may need to:

1. **Preferred:** Run `python scripts/download_docs.py` (Phase 2) — auto-downloads when URLs work.
2. **Fallback:** Download the 3 PDFs manually from the links above, save to `data/raw_pdfs/` using the filenames in the table.

**You do not need all 15–20 PDFs now** — only these 3 for Phases 2–5. We grow the corpus in Phase 6.

---

## Full corpus target (Phase 6) — document types

| Class | ~Share | Examples |
|-------|--------|----------|
| Regulatory circulars | 40% | RBI Master Directions, SEBI circulars |
| Annual reports | 40% | HDFC Bank, Reliance Industries annual reports |
| Insurance guidelines | 20% | IRDAI master circulars |

All documents must be **text-based PDFs** (not scanned images). OCR is out of scope for v1.

---

## Requirements

- Text-selectable PDFs (copy/paste works in a PDF reader)
- English language
- Publicly available (no paywall or login)
