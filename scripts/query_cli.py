#!/usr/bin/env python3
"""Ask a question against the FinDoc RAG pipeline.

Usage:
    python scripts/query_cli.py "your question"
    python scripts/query_cli.py "your question" --ticker AAPL
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from findoc.pipeline import ask
from findoc.retrieval import retrieve_tickers
from findoc.vectorstore import load_vectorstore


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the FinDoc RAG pipeline")
    parser.add_argument(
        "query",
        nargs="?",
        default="",
        help="The question to ask",
    )
    parser.add_argument(
        "--ticker",
        default=None,
        help="Restrict search to one ticker (e.g. AAPL)",
    )
    parser.add_argument(
        "--list-tickers",
        action="store_true",
        help="List available tickers and exit",
    )
    args = parser.parse_args()

    if args.list_tickers:
        vectorstore = load_vectorstore()
        for t in retrieve_tickers(vectorstore):
            print(t)
        return

    if not args.query.strip():
        print("Error: empty query.", file=sys.stderr)
        sys.exit(1)

    result = ask(args.query, ticker_filter=args.ticker)

    print(f"\nAnswer: {result.answer}\n")
    if result.citations:
        print("Citations:")
        for c in result.citations:
            print(
                f"  [{c['index']}] {c['ticker']} | {c['section']} "
                f"| source: {c['source']}"
            )
    else:
        print("(no citations present)")


if __name__ == "__main__":
    main()