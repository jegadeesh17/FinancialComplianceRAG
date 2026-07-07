# Phase Log — Financial Compliance RAG

> Full build specification: [PROJECT_SPEC.md](./PROJECT_SPEC.md)

Use this file to capture what you learned each phase.

---

## Scaffold — Project Structure & Spec

**Completed:** 2026-07-07

### What we built
- Standard project scaffold via `create_project.py`
- `docs/PROJECT_SPEC.md` — finalized technical specification (v1.0)
- `docs/PHASE_LOG.md` — this learning log
- `README.md` — standard portfolio layout
- `.env.example`, `pytest.ini`, `requirements.txt` (RAG dependencies)
- `tests/test_phase0_scaffold.py` — structure checkpoint (scaffold only)
- Connected to [github.com/jegadeesh17/FinancialComplianceRAG](https://github.com/jegadeesh17/FinancialComplianceRAG)

### Concepts
- **Compliance-first RAG:** Lead with the pain point (regulatory PDF search), not just "chat with PDFs"
- **Citations are mandatory:** In regulated finance, every AI answer needs an audit trail (doc + page)
- **Spec before code:** PROJECT_SPEC.md is the contract; phases implement against it

### Locked decisions
- Project name: `FinancialComplianceRAG`
- Corpus: ~40% regulatory / ~40% annual reports / ~20% insurance
- LLM: OpenRouter (`openrouter/free`)
- Embeddings: `all-MiniLM-L6-v2` on CPU
- Vector DB: ChromaDB
- Initial PDFs: 3 (1 RBI + 1 HDFC Bank annual report + 1 SEBI circular)

### Checkpoint command
```powershell
pytest tests/test_phase0_scaffold.py -v
```

---

## Phase 1 — Project Setup & MLOps Foundation

**Completed:** 2026-07-07

### What we built
- `src/config.py` — Pydantic Settings for paths, chunking, LLM, and embedding config
- `tests/test_phase1_setup.py` — structure, import, and config validation tests
- `docs/DATA_SOURCES.md` — where to get the 3 initial PDFs (manual vs script in Phase 2)

### Concepts
- **Pydantic Settings:** Type-safe `.env` loading with defaults and validation
- **`chroma_path` / `raw_pdf_path`:** Resolved relative to project root for portable paths
- **Chunk overlap validation:** `chunk_overlap` must stay smaller than `chunk_size`

### Checkpoint
21 tests passed.

```powershell
pip install -r requirements.txt
pytest tests/test_phase1_setup.py -v
```

---
