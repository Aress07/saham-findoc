from __future__ import annotations

from dataclasses import dataclass, field

from findoc.config import get_config
from findoc.errors import VectorStoreError
from findoc.generation import AnswerResult, generate_answer, get_llm
from findoc.logging_config import get_logger
from findoc.prompts import RAG_SYSTEM_PROMPT
from findoc.retrieval import retrieve
from findoc.vectorstore import load_vectorstore

logger = get_logger("comparison")

_COMPARISON_SYSTEM_PROMPT = """You are FinDoc, a financial document analyst assistant.

You are given findings about the SAME question, gathered separately from multiple companies' 10-K filings. Each section is labeled with the company it came from.

Write a comparison summary that:
1. States the key similarities and differences between the companies regarding the question.
2. For each company, summarizes their position in 1-2 sentences.
3. Cites claims using the [n] markers shown beside each finding.
4. Answers ONLY from the provided findings. If a finding is missing for a company, say so rather than guessing.
5. Keep the total under 300 words. Use headers for each company.

Findings:
{findings_text}

Question: {question}"""


@dataclass
class ComparisonResult:
    query: str
    per_company: dict[str, AnswerResult] = field(default_factory=dict)
    synthesis: str = ""


def _per_company_answer(row: int, ticker: str, result: AnswerResult, k: int) -> str:
    lines = [f"--- Company {row}: {ticker} ---"]
    for i, c in enumerate(result.citations, start=1):
        snippet = c["snippet"].replace("\n", " ")[:200]
        lines.append(f"[{i}] ({ticker} | {c['section']}) {snippet}")
    if not result.citations:
        lines.append(f"[no findings available for {ticker}]")
    lines.append("")
    return "\n".join(lines)


def compare_documents(query: str, tickers: list[str]) -> ComparisonResult:
    """Compare how multiple companies' filings address a question.

    Retrieves per-ticker chunks, generates a per-company grounded answer,
    then synthesizes a comparison summary with the LLM.
    """
    config = get_config()
    k = config.top_k
    if not tickers:
        raise VectorStoreError("No companies provided to compare.")
    vectorstore = load_vectorstore()
    llm = get_llm()

    result = ComparisonResult(query=query)

    findings_blocks: list[str] = []
    for row, ticker in enumerate(tickers, start=1):
        logger.info("compare: ticker=%s k=%d", ticker, k)
        filters = {"ticker": ticker}
        chunks = retrieve(query, vectorstore, k=k, filters=filters)
        if not chunks:
            logger.warning("compare: no chunks for ticker=%s query=%r", ticker, query)
            raise VectorStoreError(
                f"No content found in the {ticker} filing for that question."
            )
        per_answer = generate_answer(query, chunks, llm=llm)
        result.per_company[ticker] = per_answer
        findings_blocks.append(
            _per_company_answer(row, ticker, per_answer, k)
        )

    findings_text = "\n".join(findings_blocks)
    messages = [
        {
            "role": "system",
            "content": _COMPARISON_SYSTEM_PROMPT.format(
                findings_text=findings_text, question=query
            ),
        },
        {
            "role": "user",
            "content": f"Compare how these companies address: {query}",
        },
    ]

    response = llm.invoke(messages)
    if isinstance(response, dict):
        result.synthesis = response.get("content", "") or response.get("text", "")
    else:
        result.synthesis = getattr(response, "content", str(response))
    if isinstance(result.synthesis, list):
        result.synthesis = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in result.synthesis
        )

    return result