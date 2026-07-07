"""End-to-end RAG pipeline for question answering."""

from src.generator import generate_answer
from src.retriever import retrieve
from src.schemas import RAGResponse


def ask_question(question: str) -> RAGResponse:
    """Retrieve relevant chunks and generate a grounded answer."""
    contexts = retrieve(question)
    return generate_answer(question, contexts)
