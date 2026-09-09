import os
from pathlib import Path

import pytest

os.environ.setdefault("GROQ_API_KEY", "test")

from findoc.retrieval import retrieve, retrieve_tickers
from findoc.vectorstore import load_vectorstore

VECTOR_STORE = Path(__file__).resolve().parent.parent / "data" / "processed" / "chroma_db"


@pytest.fixture(scope="module")
def vectorstore():
    return load_vectorstore(str(VECTOR_STORE))


@pytest.mark.skipif(not VECTOR_STORE.exists(), reason="Vector store not built")
class TestRetrieve:
    def test_returns_top_k_chunks(self, vectorstore):
        docs = retrieve("What are the main risk factors?", vectorstore, k=3)
        assert 0 < len(docs) <= 3

    def test_risk_factors_query_returns_item1a(self, vectorstore):
        docs = retrieve("risk factors", vectorstore, k=5)
        sections = [d.metadata.get("section", "") for d in docs]
        assert any("Risk Factors" in s or "1A" in s for s in sections), sections

    def test_every_doc_has_metadata(self, vectorstore):
        docs = retrieve("revenue growth", vectorstore, k=3)
        for doc in docs:
            assert doc.metadata.get("ticker")
            assert doc.metadata.get("section")
            assert doc.metadata.get("source")

    def test_metadata_filter_by_ticker(self, vectorstore):
        t = retrieve_tickers(vectorstore)[0]
        docs = retrieve("business overview", vectorstore, k=5, filters={"ticker": t})
        for doc in docs:
            assert doc.metadata.get("ticker") == t

    def test_filter_returns_all_same_ticker(self, vectorstore):
        docs = retrieve("liquidity", vectorstore, k=8, filters={"ticker": "AAPL"})
        for doc in docs:
            assert doc.metadata.get("ticker") == "AAPL"

    def test_empty_query_returns_empty(self, vectorstore):
        docs = retrieve("   ", vectorstore, k=5)
        assert docs == []

    def test_relevant_query_not_empty(self, vectorstore):
        docs = retrieve("Tesla revenue recognition policy", vectorstore, k=5)
        # There is no Tesla doc, but retrieval should still return *something*
        assert len(docs) > 0

    def test_retrieve_tickers_returns_valid(self, vectorstore):
        tickers = retrieve_tickers(vectorstore)
        assert tickers
        for t in tickers:
            assert isinstance(t, str) and t.isupper()