#!/usr/bin/env python3
"""Ingest all filings in data/raw/ into a Chroma vector store.

Usage: python scripts/ingest.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from findoc.chunking import structural_split
from findoc.config import get_config
from findoc.loaders import load_all_filings
from findoc.vectorstore import build_vectorstore, vectorstore_count


def main() -> None:
    config = get_config()
    raw_dir = Path("data/raw")
    persist_dir = config.vector_store_path

    print("=== FinDoc AI Ingestion ===\n")

    print("1. Loading filings...")
    docs = load_all_filings(str(raw_dir))
    if not docs:
        print("ERROR: No filings found. Run scripts/download_sample_filings.py first.")
        sys.exit(1)
    print(f"   Loaded {len(docs)} filing(s)")

    print("2. Chunking...")
    t0 = time.time()
    chunks = []
    for doc in docs:
        doc_chunks = structural_split(doc)
        chunks.extend(doc_chunks)
        ticker = doc.metadata["ticker"]
        print(f"   {ticker}: {len(doc_chunks)} chunks")
    chunk_time = time.time() - t0
    print(f"   Total: {len(chunks)} chunks ({chunk_time:.1f}s)")

    print("3. Embedding & storing in Chroma...")
    t0 = time.time()
    vectorstore = build_vectorstore(chunks, persist_dir)
    ingest_time = time.time() - t0
    count = vectorstore_count(vectorstore)
    print(f"   Stored {count} chunks in {persist_dir} ({ingest_time:.1f}s)")

    print(f"\nDone. Vector store ready at {persist_dir}")


if __name__ == "__main__":
    main()