# Financial Intelligence Copilot
---
### **Project Overview**
**Financial Intelligence Copilot** is a dual-vertical Retrieval-Augmented Generation system for BFSI document intelligence. It ingests regulatory PDFs (RBI, SEBI) and quarterly earnings filings, embeds them into ChromaDB, and answers analyst questions via OpenRouter with **mandatory page-level source citations** and retrieval confidence signals.

**Interview pitch:** *"I built Financial Intelligence Copilot — a dual-vertical RAG system that answers compliance and earnings questions from RBI/SEBI circulars and quarterly-result PDFs, with ChromaDB retrieval, confidence gating, and auditable page-level citations."*

**Repository:** [github.com/jegadeesh17/FinancialIntelligenceCopilot](https://github.com/jegadeesh17/FinancialIntelligenceCopilot)  
**Full specification:** [docs/PROJECT_SPEC.md](docs/PROJECT_SPEC.md)  
**Learning log:** [docs/PHASE_LOG.md](docs/PHASE_LOG.md)

---
### **Key Features**
- PDF ingestion with PyMuPDF and page-level metadata (Phase 2)
- Paragraph-aware semantic chunking (800 chars / 100 overlap)
- Local CPU embeddings (`all-MiniLM-L6-v2`) + ChromaDB vector store
- Top-k retrieval with source metadata
- OpenRouter LLM generation with strict context-only prompting
- Streamlit chat UI with citation display (doc name + page)
- Checkpoint tests per phase (`pytest tests/test_phaseN_*.py`)

---
### **Dataset**
- **Corpus:** Compliance-first mixed — ~40% regulatory circulars, ~40% annual reports/10-K, ~20% insurance guidelines
- **Initial PDFs (Phase 2–3):** 1 RBI circular + 1 HDFC Bank annual report + 1 SEBI circular
- **Full target:** 15–20 PDFs by Phase 6
- **Storage:** `data/raw_pdfs/` (gitignored), vectors in `data/chroma_db/` (gitignored)
- **PDF sources:** [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)

**Sample questions:**
- *"What is the minimum capital requirement in the RBI master direction?"*
- *"What is HDFC Bank's net interest income?"*

---
### **Project Structure**
```text
FinancialIntelligenceCopilot/
├── app/app.py                  # Streamlit chat UI
├── data/
│   ├── raw_pdfs/               # PDF corpus (gitignored)
│   └── chroma_db/              # Vector store (gitignored)
├── docs/
│   ├── PROJECT_SPEC.md         # Master technical specification
│   ├── PHASE_LOG.md            # Per-phase learning notes
│   └── DATA_SOURCES.md         # PDF download guide
├── notebooks/                  # RAG workflow notebook
├── scripts/                    # Download / utility scripts
├── src/                        # Core Python modules
├── tests/                      # Phase checkpoint tests
├── requirements.txt
├── .env.example
└── README.md
```

---
### **How It Works**
1. **Ingest** — PyMuPDF extracts text from PDFs with page metadata (`src/ingest_docs.py`).
2. **Chunk** — Paragraph-aware splitting preserves semantic meaning (`src/ingest_docs.py`).
3. **Embed** — Sentence-Transformers converts chunks to vectors (`src/embeddings.py`).
4. **Store** — ChromaDB persists embeddings + metadata (`src/vectorstore.py`).
5. **Retrieve** — User query → top-5 similar chunks (`src/retriever.py`).
6. **Generate** — OpenRouter LLM answers strictly from context (`src/generator.py`).
7. **Chat** — Streamlit UI displays answer + citations (`app/app.py`).

---
### **Build Progress**
| Phase | Name | Status |
|-------|------|--------|
| 0 | Scaffold & Spec | ✅ Complete |
| 1 | Project Setup & MLOps | ✅ Complete |
| 2 | Document Ingestion | ✅ Complete |
| 3 | Embeddings & Vector Store | ✅ Complete |
| 4 | Retrieval System | ✅ Complete |
| 5 | LLM Generator | ✅ Complete |
| 6 | Streamlit Chat UI | ✅ Complete |
| 7 | Containerization (Docker) | ✅ Complete |

Run scaffold test: `pytest tests/test_phase0_scaffold.py -v`  
Full spec: [docs/PROJECT_SPEC.md](docs/PROJECT_SPEC.md)

### **3-Command Quickstart**
```powershell
cd FinancialIntelligenceCopilot
pip install -r requirements.txt
cp .env.example .env   # add OPENROUTER_API_KEY
python scripts/download_docs.py; python scripts/seed_extra_pdfs.py; python scripts/build_index.py
streamlit run app/app.py
```

**API (optional):**
```powershell
uvicorn api.main:app --port 8000
```

**Retrieval evaluation:**
```powershell
python scripts/eval_retrieval.py
```

---
### **Retrieval Evaluation**
- Eval set: `data/eval_questions.json` (10 questions)
- Script: `python scripts/eval_retrieval.py`
- Report: `reports/retrieval_eval.json` and [reports/evaluation.md](reports/evaluation.md)
- Target: ≥ 70% retrieval hit rate

---
### **Dual Vertical Expansion (Compliance + Earnings)**
- Top-5 NIFTY50 watchlist scraping for quarterly-result PDFs (Moneycontrol discovery)
- Backfill current FY quarterly filings for coverage depth
- Lightweight market snapshot (headline sentiment + basic fundamentals)
- Corpus mix check before indexing (compliance vs earnings balance)

```powershell
# 1) Latest quarterly-result scrape (top 5 NIFTY companies)
python scripts/scrape_latest_quarterly_pdfs.py

# 2) Backfill current financial-year quarterly filings
python scripts/backfill_current_fy_quarterly_pdfs.py

# 3) Optional market sentiment/fundamental snapshot
python scripts/scrape_market_sentiment.py

# 4) Validate corpus balance and rebuild vector index
python scripts/refresh_dual_vertical_index.py
```

Notes:
- `data/raw_pdfs/earnings_manifest.json` tracks scraped earnings PDFs.
- Quarterly scrapers rely on live page structure; if scrape misses links, add PDF URLs manually in the manifest and rerun index refresh.

---
### **Demo Script**
See [docs/DEMO.md](docs/DEMO.md) for a 5-minute interview demo flow.

**Quick demo loop:**
1. Ask a compliance question in Streamlit (or use sample button).
2. If confidence is LOW, run `python scripts/refresh_dual_vertical_index.py`.
3. Ask an earnings question and verify citations + vertical mix in sidebar.

---
```powershell
cd FinancialIntelligenceCopilot
pip install -r requirements.txt
cp .env.example .env   # add OPENROUTER_API_KEY
streamlit run app/app.py
```

```powershell
# Docker deployment
docker compose up --build
```

---
### **Technology Stack**
| Layer | Technology |
|-------|------------|
| PDF parsing | PyMuPDF |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (CPU) |
| Vector DB | ChromaDB |
| LLM | OpenRouter (`openrouter/free`) |
| Frontend | Streamlit |
| Config | Pydantic Settings |
| Tests | pytest |
| Deploy | Docker (Phase 7) |

---
### **Getting Started**
1. **Clone:** `git clone https://github.com/jegadeesh17/FinancialIntelligenceCopilot.git`
2. **Install:** `pip install -r requirements.txt`
3. **Configure:** `cp .env.example .env` and add your OpenRouter API key
4. **Test scaffold:** `pytest tests/test_phase0_scaffold.py -v`
5. **Notebook:** Open `notebooks/FinancialIntelligenceCopilot.ipynb`

---
### **Example Use Case**
A compliance analyst at a bank receives an updated RBI Master Direction on KYC requirements. Instead of reading 80 pages, they ask: *"What KYC documents are required for individual customers?"* The system retrieves the relevant paragraph, generates a grounded answer, and cites **RBI_Master_Direction_KYC.pdf, Page 12**.

---
### **Future Improvements**
- Hybrid BM25 + semantic search
- RAGAS faithfulness evaluation
- OCR for scanned PDFs
- Multi-collection routing (regulatory vs. filings)

---
### **Contributors**
- [jegadeesh17](https://github.com/jegadeesh17)

---
### **License**
MIT
