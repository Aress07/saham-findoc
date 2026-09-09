import os
from pathlib import Path

import pytest

os.environ.setdefault("GROQ_API_KEY", "test")

from findoc.loaders import load_10k, load_all_filings

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


@pytest.mark.skipif(not any(RAW_DIR.glob("*.htm")), reason="No sample filings in data/raw/")
class TestLoad10k:
    def test_load_returns_document(self):
        htm_file = next(RAW_DIR.glob("*.htm"))
        doc = load_10k(str(htm_file))
        assert doc.page_content
        assert isinstance(doc.page_content, str)

    def test_metadata_has_required_fields(self):
        htm_file = next(RAW_DIR.glob("*.htm"))
        doc = load_10k(str(htm_file))
        assert "ticker" in doc.metadata
        assert "fiscal_year" in doc.metadata
        assert "source" in doc.metadata
        assert "char_count" in doc.metadata
        assert doc.metadata["char_count"] > 0

    def test_metadata_ticker_from_filename(self):
        htm_file = next(RAW_DIR.glob("*.htm"))
        doc = load_10k(str(htm_file))
        expected_ticker = htm_file.stem.split("_")[0]
        assert doc.metadata["ticker"] == expected_ticker

    def test_content_is_readably_stripped(self):
        htm_file = next(RAW_DIR.glob("*.htm"))
        doc = load_10k(str(htm_file))
        content = doc.page_content
        assert "<html" not in content.lower()
        assert len(content) > 10_000

    def test_load_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_10k("data/raw/NONEXISTENT.htm")


@pytest.mark.skipif(not any(RAW_DIR.glob("*.htm")), reason="No sample filings in data/raw/")
class TestLoadAllFilings:
    def test_loads_all_filings(self):
        docs = load_all_filings(str(RAW_DIR))
        assert len(docs) >= 3

    def test_all_docs_have_content(self):
        docs = load_all_filings(str(RAW_DIR))
        for doc in docs:
            assert len(doc.page_content) > 1000
