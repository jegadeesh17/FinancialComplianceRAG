import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.chat import append_message, format_citations, init_chat_state
from src.generator import generate_answer
from src.retriever import retrieve
from src.vectorstore import get_collection_count

st.set_page_config(page_title="Financial Compliance RAG", layout="wide")
st.title("Financial Compliance RAG")
st.caption("Enterprise RAG for regulatory PDFs and financial filings.")

with st.sidebar:
    st.subheader("RAG Controls")
    top_k = st.slider("Top-k retrieval", min_value=1, max_value=10, value=5, step=1)
    show_debug = st.toggle("Show retrieved context", value=False)
    clear_chat = st.button("Clear chat")

    pdf_count = len(list((PROJECT_ROOT / "data" / "raw_pdfs").glob("*.pdf")))
    try:
        vector_count = get_collection_count()
    except Exception:
        vector_count = 0
    st.markdown("---")
    st.caption(f"Indexed chunks: **{vector_count}**")
    st.caption(f"PDFs available: **{pdf_count}**")
    if vector_count == 0:
        st.warning("Index is empty. Run `build_vector_index()` once.")

init_chat_state()
if clear_chat:
    st.session_state.messages = [st.session_state.messages[0]]
    st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("citations"):
            st.caption(format_citations(msg["citations"]))
        if msg["role"] == "assistant" and show_debug and msg.get("contexts"):
            with st.expander("Retrieved context"):
                for i, ctx in enumerate(msg["contexts"], start=1):
                    st.markdown(
                        f"**{i}.** `{ctx['source']}` p.{ctx['page']} | score={ctx['score']:.4f}\n\n"
                        f"{ctx['text'][:320]}..."
                    )

if prompt := st.chat_input("Ask a compliance question..."):
    append_message("user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving context and generating answer..."):
            try:
                contexts = retrieve(prompt, top_k=top_k)
                response = generate_answer(prompt, contexts)
                st.markdown(response.answer)
                if response.citations:
                    st.caption(format_citations(response.citations))
                append_message("assistant", response.answer, response.citations)
                st.session_state.messages[-1]["contexts"] = [
                    {
                        "source": c.source,
                        "page": c.page,
                        "score": c.score,
                        "text": c.text,
                    }
                    for c in contexts
                ]
            except Exception as exc:  # pragma: no cover
                message = f"Error: {exc}"
                st.error(message)
                append_message("assistant", message, [])
