from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from langchain_core.documents import Document
from langchain_groq import ChatGroq

from findoc.config import get_config
from findoc.errors import ConfigurationError, GenerationError
from findoc.logging_config import get_logger
from findoc.prompts import build_chat_messages

_CITATION_PATTERN = re.compile(r"[\[\u3010]\s*(\d+)\s*[\]\u3011]")

logger = get_logger("generation")


@dataclass
class AnswerResult:
    query: str
    answer: str
    citations: list[dict] = field(default_factory=list)


@lru_cache(maxsize=1)
def get_llm() -> ChatGroq:
    """Return a configured Groq chat model."""
    config = get_config()
    if not config.groq_api_key:
        logger.error("GROQ_API_KEY is not set")
        raise ConfigurationError(
            "Missing GROQ_API_KEY. Add it to your .env file (see .env.example)."
        )
    return ChatGroq(
        groq_api_key=config.groq_api_key,
        model=config.llm_model,
        temperature=0.1,
        max_retries=2,
    )


def _extract_citations(answer: str, chunks: list[Document]) -> list[dict]:
    """Map [n] markers in the answer back to source chunk metadata."""
    citations: list[dict] = []
    seen: set[int] = set()

    for match in _CITATION_PATTERN.finditer(answer):
        idx = int(match.group(1))
        if idx in seen or idx < 1 or idx > len(chunks):
            continue
        seen.add(idx)
        chunk = chunks[idx - 1]
        meta = chunk.metadata
        citations.append(
            {
                "index": idx,
                "source": meta.get("source", ""),
                "ticker": meta.get("ticker", ""),
                "section": meta.get("section", ""),
                "snippet": chunk.page_content[:300],
            }
        )

    return citations


def generate_answer(
    query: str,
    chunks: list[Document],
    llm: ChatGroq | None = None,
) -> AnswerResult:
    """Generate a grounded answer with citations using Groq."""
    if llm is None:
        llm = get_llm()

    messages = build_chat_messages(query, chunks)
    try:
        response = llm.invoke(messages)
    except Exception as exc:  # network, timeout, rate limit, API errors
        logger.error("LLM call failed: %s", exc, exc_info=True)
        raise GenerationError(
            "The language model request failed (network, timeout, or rate "
            "limit). Please try again in a few seconds."
        ) from exc

    if isinstance(response, dict):
        answer_text = response.get("content", "") or response.get("text", "")
    else:
        answer_text = getattr(response, "content", str(response))

    if isinstance(answer_text, list):
        answer_text = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in answer_text
        )

    citations = _extract_citations(answer_text, chunks)

    return AnswerResult(query=query, answer=str(answer_text), citations=citations)