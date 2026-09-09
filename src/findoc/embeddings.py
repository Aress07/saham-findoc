from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings

from findoc.config import get_config

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_config_singleton():
    return get_config()


@lru_cache(maxsize=1)
def get_embedding_function() -> Embeddings:
    """Return the configured embedding function (local sentence-transformers)."""
    config = get_config()
    provider = config.embedding_provider.lower()

    if provider not in ("local", "huggingface", "sentence-transformers"):
        raise ValueError(
            f"Unsupported embedding_provider: {provider}. "
            f"Use 'local' for free sentence-transformers embeddings."
        )

    return HuggingFaceEmbeddings(model_name=DEFAULT_MODEL)


def embedding_dimension() -> int:
    """Return the dimensionality of the embedding model's vectors."""
    return 384  # all-MiniLM-L6-v2 produces 384-dim vectors