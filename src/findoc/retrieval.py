from __future__ import annotations

from langchain_core.documents import Document
from langchain_chroma import Chroma


def retrieve(
    query: str,
    vectorstore: Chroma,
    k: int,
    filters: dict | None = None,
) -> list[Document]:
    """Retrieve the top-k most relevant chunks for a query.

    Args:
        query: Natural-language search query.
        vectorstore: Loaded Chroma vector store.
        k: Number of results to return.
        filters: Optional metadata filter dict (e.g. {"ticker": "AAPL"}).

    Returns:
        List of retrieved Documents with metadata attachments.
    """
    if not query.strip():
        return []

    if filters:
        results = vectorstore.similarity_search_with_score(
            query=query, k=k, filter=filters
        )
        docs = [doc for doc, _score in results]
    else:
        docs = vectorstore.similarity_search(query=query, k=k)

    return docs


def retrieve_tickers(vectorstore: Chroma) -> list[str]:
    """Return the distinct tickers present in the vector store."""
    collection = vectorstore._collection
    meta = collection.get(include=["metadatas"])
    tickers = {
        m.get("ticker") for m in meta["metadatas"] if m and m.get("ticker")
    }
    return sorted(tickers)