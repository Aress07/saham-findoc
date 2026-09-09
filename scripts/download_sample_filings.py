#!/usr/bin/env python3
"""Download sample 10-K filings from SEC EDGAR into data/raw/.

Usage: python scripts/download_sample_filings.py [--tickers AAPL MSFT AMZN]
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import requests

USER_AGENT = "FinDocAI/1.0 (taham@example.com)"
HEADERS = {"User-Agent": USER_AGENT}

DEFAULT_TICKERS = ["AAPL", "MSFT", "AMZN"]
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def _get_cik(ticker: str) -> str:
    """Resolve ticker to CIK number via EDGAR company tickers JSON."""
    url = "https://www.sec.gov/files/company_tickers.json"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    for entry in data.values():
        if entry["ticker"] == ticker:
            return str(entry["cik_str"]).zfill(10)
    raise ValueError(f"Ticker {ticker} not found in EDGAR")


def _find_latest_10k_url(cik: str, ticker: str) -> tuple[str, str] | None:
    """Find the most recent 10-K filing primary document URL."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    documents = recent.get("primaryDocument", [])
    filing_dates = recent.get("filingDate", [])

    for i, form in enumerate(forms):
        if form == "10-K":
            acc = accessions[i]
            doc = documents[i]
            date = filing_dates[i]
            acc_clean = acc.replace("-", "")
            cik_num = str(int(cik))
            file_url = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{acc_clean}/{doc}"
            return file_url, date
    return None


def download_filing(ticker: str) -> Path | None:
    out_path = RAW_DIR / f"{ticker}_10K.htm"
    if out_path.exists() and out_path.stat().st_size > 50_000:
        print(f"  [SKIP] {ticker} already downloaded ({out_path.stat().st_size:,} bytes)")
        return out_path

    print(f"  Resolving CIK for {ticker}... ", end="", flush=True)
    try:
        cik = _get_cik(ticker)
        print(f"CIK {cik}")
    except Exception as e:
        print(f"FAILED: {e}")
        return None

    time.sleep(0.3)

    print(f"  Finding latest 10-K for {ticker}... ", end="", flush=True)
    try:
        result = _find_latest_10k_url(cik, ticker)
        if result is None:
            print("NO 10-K FOUND")
            return None
        url, date = result
        print(f"filing date {date}")
    except Exception as e:
        print(f"FAILED: {e}")
        return None

    time.sleep(0.3)

    print(f"  Downloading {ticker} 10-K... ", end="", flush=True)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=120)
        resp.raise_for_status()
        out_path.write_bytes(resp.content)
        size = out_path.stat().st_size
        print(f"done ({size:,} bytes)")
        time.sleep(0.5)
        return out_path
    except requests.RequestException as e:
        print(f"FAILED: {e}")
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Download sample 10-K filings from SEC EDGAR")
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=DEFAULT_TICKERS,
        help="Tickers to download (default: AAPL MSFT AMZN)",
    )
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Downloading sample 10-K filings from SEC EDGAR ===\n")
    success = 0
    for ticker in args.tickers:
        result = download_filing(ticker)
        if result:
            success += 1

    print(f"\nDone: {success}/{len(args.tickers)} filings downloaded to {RAW_DIR}")

    if success == 0:
        print("ERROR: No filings downloaded.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
