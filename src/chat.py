"""Helpers for Streamlit chat session state and citation formatting."""

from __future__ import annotations

import streamlit as st

from src.schemas import Citation

WELCOME_MESSAGE = (
    "Hello! Ask me about RBI/SEBI regulations or financial report disclosures. "
    "I will answer with source citations."
)


def init_chat_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": WELCOME_MESSAGE, "citations": []}]


def append_message(role: str, content: str, citations: list[Citation] | list[dict] | None = None) -> None:
    st.session_state.messages.append(
        {
            "role": role,
            "content": content,
            "citations": citations or [],
        }
    )


def format_citations(citations: list[Citation] | list[dict]) -> str:
    if not citations:
        return "Sources: none"
    grouped: dict[str, set[int]] = {}
    for c in citations:
        source = c.source if hasattr(c, "source") else c.get("source", "")
        page = int(c.page if hasattr(c, "page") else c.get("page", 0))
        grouped.setdefault(source, set()).add(page)

    parts = []
    for source, pages in grouped.items():
        ordered = sorted(p for p in pages if p > 0)
        page_text = ",".join(str(p) for p in ordered[:5])
        if len(ordered) > 5:
            page_text += ",..."
        parts.append(f"{source} (p.{page_text})")
    return "Sources: " + " | ".join(parts)
