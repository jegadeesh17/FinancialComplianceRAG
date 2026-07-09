import json
import sys
import time
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.chat import append_message, format_citations, init_chat_state
from src.corpus_stats import classify_pdf_names, summarize_corpus
from src.generator import generate_answer
from src.indexing import read_index_metadata
from src.retriever import get_best_score, is_low_confidence, retrieve
from src.telemetry import log_query
from src.vectorstore import build_vector_index, get_chroma_client, get_collection_count, get_or_create_collection

RAW_PDF_DIR = PROJECT_ROOT / "data" / "raw_pdfs"
MARKET_SNAPSHOT_PATH = PROJECT_ROOT / "data" / "market_signals" / "moneycontrol_top5_snapshot.json"

COMPLIANCE_SAMPLE = "What KYC documents are required for individual customers?"
EARNINGS_SAMPLE = "What was HDFC Bank net interest income in the annual report?"

st.set_page_config(page_title="Financial Intelligence Copilot", layout="wide")
st.title("Financial Intelligence Copilot")
st.caption("Dual-vertical RAG for compliance circulars and quarterly earnings filings.")


def _load_market_snapshot() -> dict:
    if not MARKET_SNAPSHOT_PATH.exists():
        return {}
    try:
        return json.loads(MARKET_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _vertical_for_filename(filename: str, manifest_map: dict[str, dict]) -> str:
    row = manifest_map.get(filename, {})
    if filename.startswith("earnings_") or row.get("vertical") == "earnings":
        return "earnings"
    return "compliance"


def _confidence_badge(low_confidence: bool) -> None:
    if low_confidence:
        st.error("Retrieval confidence: LOW")
    else:
        st.success("Retrieval confidence: OK")


def _run_query(prompt: str, top_k: int, max_distance: float) -> None:
    append_message("user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving context and generating answer..."):
            start = time.perf_counter()
            try:
                contexts = retrieve(prompt, top_k=top_k, max_distance=max_distance)
                response = generate_answer(prompt, contexts)
                low_confidence = is_low_confidence(contexts)
                best_score = get_best_score(contexts)

                _confidence_badge(low_confidence)
                st.markdown("**Summary**")
                st.markdown(response.answer)

                if low_confidence:
                    suffix = f" (best distance={best_score:.4f})" if best_score is not None else ""
                    st.warning(
                        "Evidence may be stale or too weak"
                        f"{suffix}. Run refresh scripts and retry."
                    )

                st.markdown("**Citations**")
                st.caption(format_citations(response.citations))

                append_message("assistant", response.answer, response.citations)
                st.session_state.messages[-1]["contexts"] = [
                    {
                        "source": c.source,
                        "page": c.page,
                        "score": c.score,
                        "text": c.text,
                        "document_vertical": c.document_vertical,
                    }
                    for c in contexts
                ]
                st.session_state.messages[-1]["low_confidence"] = low_confidence
                st.session_state.messages[-1]["best_score"] = best_score

                latency_ms = (time.perf_counter() - start) * 1000
                top_sources = [c.source for c in contexts[:top_k]]
                fallback_used = (
                    len(contexts) == 0
                    or "could not find relevant context" in response.answer.lower()
                    or low_confidence
                )
                log_query(prompt, top_sources=top_sources, fallback_used=fallback_used, latency_ms=latency_ms)
                if fallback_used:
                    st.info("Insufficient evidence found. Try a sample query or refresh the corpus.")
            except Exception as exc:  # pragma: no cover
                message = f"Error: {exc}"
                st.error(message)
                append_message("assistant", message, [])


with st.sidebar:
    st.subheader("RAG Controls")
    top_k = st.slider("Top-k retrieval", min_value=1, max_value=10, value=5, step=1)
    max_distance = st.slider("Max retrieval distance", min_value=0.0, max_value=2.0, value=1.2, step=0.05)
    show_debug = st.toggle("Show retrieved context", value=False)
    clear_chat = st.button("Clear chat")

    corpus_stats = summarize_corpus(RAW_PDF_DIR)
    try:
        vector_count = get_collection_count()
    except Exception:
        vector_count = 0
    meta = read_index_metadata()
    snapshot = _load_market_snapshot()

    st.markdown("---")
    st.subheader("Vertical view")
    vc = corpus_stats.get("vertical_counts", {})
    st.metric("Compliance PDFs", vc.get("compliance", 0))
    st.metric("Earnings PDFs", vc.get("earnings", 0))
    st.caption(f"Earnings ratio: **{corpus_stats.get('earnings_ratio', 0.0):.2f}**")

    companies = corpus_stats.get("company_counts", {})
    if companies:
        top_companies = ", ".join(f"{k} ({v})" for k, v in sorted(companies.items(), key=lambda x: -x[1])[:5])
        st.caption(f"Companies indexed: **{top_companies}**")
    else:
        st.caption("Companies indexed: none yet (run earnings scrapers)")

    if snapshot.get("as_of"):
        st.caption(f"Market snapshot: **{snapshot['as_of']}**")
    else:
        st.caption("Market snapshot: not generated")

    st.markdown("---")
    st.caption(f"Indexed chunks: **{vector_count}**")
    st.caption(f"Last indexed: **{meta.get('last_indexed_at', 'unknown')}**")

    if vector_count == 0:
        st.warning("Index is empty. Run `python scripts/build_index.py` once.")

    confirm_rebuild = st.checkbox("Confirm rebuild index")
    if st.button("Rebuild index", disabled=not confirm_rebuild):
        with st.spinner("Rebuilding vector index..."):
            stored = build_vector_index()
        st.success(f"Rebuilt index with {stored} chunks.")
        st.rerun()

init_chat_state()
if clear_chat:
    st.session_state.messages = [st.session_state.messages[0]]
    st.rerun()

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

main_col, docs_col = st.columns([3, 2])

with main_col:
    st.subheader("Ask")
    q1, q2 = st.columns(2)
    if q1.button("Compliance sample query", use_container_width=True):
        st.session_state.pending_prompt = COMPLIANCE_SAMPLE
    if q2.button("Earnings sample query", use_container_width=True):
        st.session_state.pending_prompt = EARNINGS_SAMPLE

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                _confidence_badge(bool(msg.get("low_confidence")))
                st.markdown("**Summary**")
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                st.markdown("**Citations**")
                st.caption(format_citations(msg.get("citations", [])))
            if msg["role"] == "assistant" and show_debug and msg.get("contexts"):
                with st.expander("Retrieved context"):
                    for i, ctx in enumerate(msg["contexts"], start=1):
                        vertical = ctx.get("document_vertical", "compliance")
                        st.markdown(
                            f"**{i}.** [{vertical}] `{ctx['source']}` p.{ctx['page']} "
                            f"| score={ctx['score']:.4f}\n\n{ctx['text'][:320]}..."
                        )

    if st.session_state.pending_prompt:
        prompt = st.session_state.pending_prompt
        st.session_state.pending_prompt = None
        _run_query(prompt, top_k=top_k, max_distance=max_distance)
    elif prompt := st.chat_input("Ask a compliance or earnings question..."):
        _run_query(prompt, top_k=top_k, max_distance=max_distance)

with docs_col:
    st.subheader("Document Management")
    manifest_map: dict[str, dict] = {}
    manifest_path = RAW_PDF_DIR / "earnings_manifest.json"
    if manifest_path.exists():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_map = {d.get("filename", ""): d for d in payload.get("downloads", [])}
        except Exception:
            manifest_map = {}

    pdf_files = sorted(RAW_PDF_DIR.glob("*.pdf"))
    collection = get_or_create_collection(get_chroma_client())
    rows = collection.get(include=["metadatas"])
    counts: dict[str, int] = {}
    for md in rows.get("metadatas", []):
        if not md:
            continue
        source = str(md.get("source", ""))
        counts[source] = counts.get(source, 0) + 1

    compliance_names, earnings_names = classify_pdf_names(RAW_PDF_DIR)
    st.caption(f"Compliance: **{len(compliance_names)}** | Earnings: **{len(earnings_names)}**")

    docs_data = []
    for pdf_file in pdf_files:
        chunk_count = counts.get(pdf_file.name, 0)
        vertical = _vertical_for_filename(pdf_file.name, manifest_map)
        docs_data.append(
            {
                "Vertical": vertical,
                "Document": pdf_file.name,
                "SizeMB": round(pdf_file.stat().st_size / (1024 * 1024), 2),
                "IndexedChunks": chunk_count,
                "Status": "Indexed" if chunk_count > 0 else "Pending",
            }
        )
    if docs_data:
        st.dataframe(docs_data, use_container_width=True, hide_index=True)
    else:
        st.info("No PDFs found in data/raw_pdfs.")

    with st.expander("Refresh corpus (offline)"):
        st.code(
            "python scripts/scrape_latest_quarterly_pdfs.py\n"
            "python scripts/backfill_current_fy_quarterly_pdfs.py\n"
            "python scripts/refresh_dual_vertical_index.py",
            language="powershell",
        )
