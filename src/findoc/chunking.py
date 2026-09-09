from __future__ import annotations

import re
import unicodedata

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from findoc.config import get_config

_ITEM_PATTERN = re.compile(r"^\s*(?:Item|ITEM)\s+(1[0-6]|[1-9])([A-Za-z]?)\.?\s*")


def _extract_section_title(header_line: str) -> str:
    """Convert 'Item 1A.\xa0\xa0\xa0\xa0Risk Factors' -> 'Item 1A. Risk Factors'."""
    text = unicodedata.normalize("NFKC", header_line).strip()
    easy_match = re.match(r"^(Item\s+\d{1,2}[A-Za-z]?)\.?\s*\S", text)
    if easy_match:
        label = easy_match.group(1)
        rest = text[easy_match.end() - 1:]
        rest = rest.strip(" \xa0.:-")
        return f"{label}. {rest}" if rest else label
    return text


def _find_section_boundaries(text: str) -> list[tuple[int, str, str]]:
    """Return (start_offset, item_label, title) for each body section.

    Uses the LAST occurrence of each Item N label so table-of-contents
    entries (which appear earlier) are ignored.
    """
    lines = text.split("\n")
    offset = 0
    last_occurrence: dict[str, dict] = {}

    for line in lines:
        m = _ITEM_PATTERN.match(line)
        if m:
            item_label = f"{int(m.group(1))}{m.group(2).upper()}"
            last_occurrence[item_label] = {
                "offset": offset,
                "title": _extract_section_title(line),
            }
        offset += len(line) + 1

    boundaries: list[tuple[int, str, str]] = []
    for label in sorted(last_occurrence, key=lambda x: last_occurrence[x]["offset"]):
        info = last_occurrence[label]
        boundaries.append((info["offset"], label, info["title"]))

    boundaries.sort(key=lambda x: x[0])
    return boundaries


def structural_split(document: Document) -> list[Document]:
    """Split a 10-K Document into section-aware chunks.

    Content before the first Item N header becomes a 'Preamble' chunk.
    Sections larger than config.chunk_size are further split with
    RecursiveCharacterTextSplitter using configured chunk_size/overlap.
    """
    config = get_config()
    text = document.page_content
    boundaries = _find_section_boundaries(text)

    sections: list[tuple[str, str, str]] = []
    for i, (start, label, title) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        section_text = text[start:end].strip()
        sections.append((label, title, section_text))

    if boundaries:
        preamble = text[: boundaries[0][0]].strip()
        if preamble:
            sections.insert(0, ("PRE", "Preamble", preamble))

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    base_meta = {k: v for k, v in document.metadata.items() if k != "char_count"}
    chunks: list[Document] = []

    for i, (label, title, section_text) in enumerate(sections):
        meta = dict(base_meta)

        label_part = title if title.startswith("Item") else f"Item {label}"
        section_label = title if title else label

        if len(section_text) <= config.chunk_size:
            meta.update({"section": section_label, "section_number": label, "chunk_id": f"{i:04d}"})
            chunks.append(Document(page_content=section_text, metadata=meta))
        else:
            sub_docs = splitter.split_text(section_text)
            for j, sub in enumerate(sub_docs):
                meta_j = dict(meta)
                meta_j.update(
                    {"section": section_label, "section_number": label, "chunk_id": f"{i:04d}_{j:02d}"}
                )
                chunks.append(Document(page_content=sub, metadata=meta_j))

    return chunks