from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings

from findoc.config import get_config

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


class FastEmbedEmbeddings(Embeddings):
    """LangChain-compatible embeddings backed by FastEmbed (ONNX).

    Runs locally with onnxruntime — no torch/GPU dependency, keeping the
    container small and memory-light on constrained hosts (e.g. Render free).
    """

    def __init__(self, model_name: str = DEFAULT_MODEL, **kwargs) -> None:
        from fastembed import TextEmbedding  # deferred import (heavy backends)

        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name, **kwargs)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vec.tolist() for vec in self._model.passage_embed(list(texts))]

    def embed_query(self, text: str) -> list[float]:
        return next(iter(self._model.query_embed(text))).tolist()


@lru_cache(maxsize=1)
def _get_config_singleton():
    return get_config()


@lru_cache(maxsize=1)
def get_embedding_function() -> Embeddings:
    """Return the configured embedding function (local FastEmbed/ONNX)."""
    config = get_config()
    provider = config.embedding_provider.lower()

    if provider not in ("local", "fastembed", "onnx"):
        raise ValueError(
            f"Unsupported embedding_provider: {provider}. "
            f"Use 'local' for free FastEmbed (ONNX) embeddings."
        )

    return FastEmbedEmbeddings(model_name=DEFAULT_MODEL)


def embedding_dimension() -> int:
    """Return the dimensionality of the embedding model's vectors."""
    return 384  # BAAI/bge-small-en-v1.5 produces 384-dim vectors