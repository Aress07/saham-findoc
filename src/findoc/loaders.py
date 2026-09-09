from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup
from langchain_core.documents import Document


def _parse_filename(filepath: str) -> dict[str, str]:
    """Extract ticker and fiscal year from filename like AAPL_10K.htm."""
    stem = Path(filepath).stem  # e.g. AAPL_10K
    parts = stem.split("_")
    ticker = parts[0] if parts else "UNKNOWN"
    year = parts[2] if len(parts) > 2 else "UNKNOWN"
    return {"ticker": ticker, "fiscal_year": year}


def _strip_html(html: str) -> str:
    """Remove HTML/XBRL tags, keep readable text."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "head"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def load_10k(filepath: str) -> Document:
    """Load a 10-K filing (HTML) and return a LangChain Document."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Filing not found: {filepath}")

    raw_html = path.read_text(encoding="utf-8", errors="ignore")
    text = _strip_html(raw_html)

    meta = _parse_filename(filepath)
    meta["source"] = str(path)
    meta["char_count"] = len(text)

    return Document(page_content=text, metadata=meta)


def load_all_filings(data_dir: str = "data/raw") -> list[Document]:
    """Load all .htm/.html filings from a directory."""
    data_path = Path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    docs = []
    for f in sorted(data_path.glob("*.htm")) + sorted(data_path.glob("*.html")):
        docs.append(load_10k(str(f)))

    return docs
