"""Sentence-Transformer embeddings for document chunks."""

from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from src.config import Settings, get_settings

# all-MiniLM-L6-v2 output dimension
EMBEDDING_DIMENSION = 384


@lru_cache
def get_embedding_model(model_name: str) -> SentenceTransformer:
    """Load and cache the embedding model (downloads on first use)."""
    return SentenceTransformer(model_name)


def embed_texts(
    texts: list[str],
    settings: Settings | None = None,
) -> list[list[float]]:
    """Convert text strings to embedding vectors."""
    if not texts:
        return []

    settings = settings or get_settings()
    model = get_embedding_model(settings.embedding_model)
    vectors = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return [vector.tolist() for vector in vectors]


def embed_query(
    query: str,
    settings: Settings | None = None,
) -> list[float]:
    """Embed a single user query."""
    return embed_texts([query], settings=settings)[0]
