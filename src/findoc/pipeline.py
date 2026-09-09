from __future__ import annotations

import time
from functools import lru_cache

from langchain_chroma import Chroma

from findoc.config import get_config
from findoc.errors import GenerationError, VectorStoreError
from findoc.generation import AnswerResult, generate_answer, get_llm
from findoc.logging_config import get_logger
from findoc.retrieval import retrieve
from findoc.vectorstore import load_vectorstore

logger = get_logger("pipeline")


@lru_cache(maxsize=1)
def _get_vectorstore() -> Chroma:
    try:
        return load_vectorstore()
    except FileNotFoundError as exc:
        raise VectorStoreError(
            "Vector store not found. Run `python scripts/ingest.py` to build it."
        ) from exc
    except Exception as exc:
        raise VectorStoreError(f"Failed to load vector store: {exc}") from exc


def ask(query: str, ticker_filter: str | None = None, k: int | None = None) -> AnswerResult:
    """End-to-end RAG: vectorstore -> retrieve -> generate.

    Args:
        query: The user's question.
        ticker_filter: Optional ticker to restrict retrieval (e.g. "AAPL").
        k: Number of chunks to retrieve (defaults to config.top_k).

    Returns:
        AnswerResult with answer text and citation mapping.

    Raises:
        VectorStoreError: if the vector store is missing/empty.
        GenerationError: if the LLM call fails.
    """
    config = get_config()
    k = k or config.top_k

    logger.info("ask: query=%r ticker=%s k=%d", query, ticker_filter, k)
    t0 = time.time()
    try:
        vectorstore = _get_vectorstore()
        filters = {"ticker": ticker_filter} if ticker_filter else None
        chunks = retrieve(query, vectorstore, k=k, filters=filters)
    except VectorStoreError:
        raise
    except Exception as exc:
        logger.error("retrieval failed: %s", exc, exc_info=True)
        raise VectorStoreError(
            "Failed to search the filings. Please try again."
        ) from exc

    if not chunks:
        logger.warning("no chunks retrieved for query=%r", query)
        raise VectorStoreError(
            "No relevant content was found in the filings for that question."
        )

    llm = get_llm()
    try:
        result = generate_answer(query, chunks, llm=llm)
    except GenerationError:
        raise
    except Exception as exc:
        logger.error("generation failed: %s", exc, exc_info=True)
        raise GenerationError(
            "Answer generation failed. Please try again in a few seconds."
        ) from exc

    elapsed = time.time() - t0
    logger.info(
        "ask done: query=%r chunks=%d citations=%d %.1fs",
        query,
        len(chunks),
        len(result.citations),
        elapsed,
    )
    return result