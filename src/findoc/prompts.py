from __future__ import annotations

from langchain_core.documents import Document

RAG_SYSTEM_PROMPT = """You are FinDoc, a financial document analyst assistant.

Your job is to answer questions about financial documents (10-K filings) using ONLY the context provided below. The context consists of numbered passages extracted from real filings.

STRICT RULES:
1. Answer ONLY from the provided context. Never use outside knowledge, guesses, or training data about a specific company's numbers.
2. If the context does not contain the answer, respond exactly: "I don't have this information in the provided documents."
3. Never invent or extrapolate numbers, dates, or facts that are not in the context.
4. Cite sources: after every claim, add a bracketed citation number like [1] that refers to the corresponding numbered context passage. Use the passage number shown beside each chunk.
5. Keep the answer concise and directly relevant to the question. Use bullet points when useful.
6. If asked to summarize or compare, structure the answer clearly using the provided sections.
7. If the answer draws from multiple passages, cite each one.

Context passages:
{context_text}
"""


def build_prompt(query: str, chunks: list[Document]) -> str:
    """Render the numbered context and return the full prompt for the user message.

    Each chunk is prefixed with [n] where n is its 1-based index. Both the
    system prompt and the user message get the chunk text, and the model is
    told to cite those indices.
    """
    context_lines = []
    for i, chunk in enumerate(chunks, start=1):
        context_lines.append(f"[{i}] {chunk.page_content}")
    context_text = "\n\n".join(context_lines)

    system_block = RAG_SYSTEM_PROMPT.format(context_text=context_text)

    user_message = f"""Question: {query}

Answer using ONLY the numbered context passages above. Cite each claim with the corresponding [number]."""

    return f"{system_block}\n\n{user_message}"


def build_chat_messages(query: str, chunks: list[Document]) -> list[dict]:
    """Return (system, user) messages for a chat API call."""
    system = RAG_SYSTEM_PROMPT.format(
        context_text="\n\n".join(
            f"[{i}] {c.page_content}" for i, c in enumerate(chunks, start=1)
        )
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": query},
    ]