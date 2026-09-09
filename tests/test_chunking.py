import os
from pathlib import Path

import pytest

os.environ.setdefault("GROQ_API_KEY", "test")

from findoc.chunking import structural_split
from findoc.loaders import load_10k

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


@pytest.fixture(scope="module")
def sample_doc():
    htm_file = sorted(RAW_DIR.glob("*.htm"))[0]
    return load_10k(str(htm_file))


@pytest.mark.skipif(not any(RAW_DIR.glob("*.htm")), reason="No sample filings in data/raw/")
class TestStructuralSplit:
    def test_returns_multiple_chunks(self, sample_doc):
        chunks = structural_split(sample_doc)
        assert len(chunks) >= 10

    def test_every_chunk_has_section_metadata(self, sample_doc):
        chunks = structural_split(sample_doc)
        for chunk in chunks:
            assert "section" in chunk.metadata
            assert chunk.metadata["section"]

    def test_chunks_carry_source_metadata(self, sample_doc):
        chunks = structural_split(sample_doc)
        for chunk in chunks:
            assert chunk.metadata["source"]
            assert chunk.metadata["ticker"]
            assert chunk.metadata["fiscal_year"]

    def test_section_detection_risk_factors(self, sample_doc):
        chunks = structural_split(sample_doc)
        sections = {c.metadata["section"] for c in chunks}
        risk_found = any("Risk Factors" in s for s in sections)
        assert risk_found, f"Expected Risk Factors section, got: {sections}"

    def test_each_chunk_has_unique_id(self, sample_doc):
        chunks = structural_split(sample_doc)
        ids = [c.metadata["chunk_id"] for c in chunks]
        assert len(ids) == len(set(ids))

    def test_all_chunks_have_content(self, sample_doc):
        chunks = structural_split(sample_doc)
        for chunk in chunks:
            assert len(chunk.page_content) > 0

    def test_preamble_or_item1_section_exists(self, sample_doc):
        chunks = structural_split(sample_doc)
        sections = [c.metadata["section"] for c in chunks]
        assert any("Business" in s or s == "Preamble" for s in sections)

    def test_spot_check_reconstructed_length(self, sample_doc):
        chunks = structural_split(sample_doc)
        reconstructed = sum(len(c.page_content) for c in chunks)
        original = len(sample_doc.page_content)
        # Allow some loss from TOC/headers being swallowed into boundary lines
        assert reconstructed > original * 0.85, (
            f"Reconstructed {reconstructed} vs original {original}"
        )