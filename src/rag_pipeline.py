"""End-to-end RAG pipeline for question answering."""

from src.generator import generate_answer
from src.retriever import get_best_score, is_low_confidence, retrieve
from src.schemas import RAGResponse


def ask_question(question: str) -> RAGResponse:
    """Retrieve relevant chunks and generate a grounded answer."""
    contexts = retrieve(question)
    response = generate_answer(question, contexts)
    response.low_confidence = is_low_confidence(contexts)
    response.best_score = get_best_score(contexts)
    return response
