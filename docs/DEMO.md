# Financial Intelligence Copilot — 5-Minute Demo Script

## Prerequisites
```powershell
cd FinancialIntelligenceCopilot
pip install -r requirements.txt
cp .env.example .env   # set OPENROUTER_API_KEY
python scripts/download_docs.py
python scripts/seed_extra_pdfs.py
python scripts/build_index.py
```

Optional earnings vertical setup:
```powershell
python scripts/scrape_latest_quarterly_pdfs.py
python scripts/backfill_current_fy_quarterly_pdfs.py
python scripts/refresh_dual_vertical_index.py
```

## Demo Flow (5 minutes)

### 1. Show retrieval evaluation (30 sec)
```powershell
python scripts/eval_retrieval.py
```
Point out hit rate ≥ 70% and `reports/retrieval_eval.json`.

### 2. Streamlit dual-vertical chat (2 min)
```powershell
streamlit run app/app.py
```

**Compliance walkthrough**
1. Click **Compliance sample query** (or ask manually):
   - *"What KYC documents are required for individual customers?"*
2. Show:
   - answer + citations
   - confidence badge (`OK` or `LOW`)
   - sidebar compliance/earnings counts

**Earnings walkthrough**
1. Click **Earnings sample query** (or ask manually):
   - *"What was HDFC Bank net interest income in the annual report?"*
2. Show document table `Vertical` column and company list in sidebar.

**If confidence is LOW**
```powershell
python scripts/refresh_dual_vertical_index.py
```
Ask the same question again and compare confidence/citations.

### 3. FastAPI endpoint (1 min)
```powershell
uvicorn api.main:app --port 8000
```
In another terminal:
```powershell
curl http://localhost:8000/health
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d "{\"question\": \"What are AML customer due diligence requirements?\"}"
```
Verify `/health` includes `corpus` and `/ask` includes `low_confidence` + `best_score`.

### 4. Architecture talking points (1 min)
- PDF ingest → chunk → embed → ChromaDB → retrieve → OpenRouter generate
- Dual vertical corpus: compliance circulars + quarterly earnings PDFs
- Confidence gating + citation guardrails + pytest checkpoints

## Interview Close
*"I built Financial Intelligence Copilot — a dual-vertical RAG system with auditable page-level citations, retrieval confidence gating, and measured retrieval quality on a 10-question eval set."*
