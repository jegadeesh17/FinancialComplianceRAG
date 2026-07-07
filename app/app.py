import streamlit as st

from src.chat import append_message, format_citations, init_chat_state
from src.rag_pipeline import ask_question

st.set_page_config(page_title="Financial Compliance RAG", layout="wide")
st.title("Financial Compliance RAG")
st.caption("Enterprise RAG for regulatory PDFs and financial filings.")

init_chat_state()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("citations"):
            st.caption(format_citations(msg["citations"]))

if prompt := st.chat_input("Ask a compliance question..."):
    append_message("user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving context and generating answer..."):
            try:
                response = ask_question(prompt)
                st.markdown(response.answer)
                if response.citations:
                    st.caption(format_citations(response.citations))
                append_message("assistant", response.answer, response.citations)
            except Exception as exc:  # pragma: no cover
                message = f"Error: {exc}"
                st.error(message)
                append_message("assistant", message, [])
