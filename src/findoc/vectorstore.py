from __future__ import annotations

from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

from findoc.config import get_config
from findoc.embeddings import get_embedding_function


def build_vectorstore(documents: list[Document], persist_dir: str | None = None) -> Chroma:
    """Embed documents and persist them into a Chroma vector store."""
    config = get_config()
    path = persist_dir or config.vector_store_path
    embedding = get_embedding_function()

    _clean_persist_dir(path)

    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embedding,
        persist_directory=path,
    )
    return vectorstore


def load_vectorstore(persist_dir: str | None = None) -> Chroma:
    """Load an existing Chroma vector store from disk."""
    config = get_config()
    path = persist_dir or config.vector_store_path

    if not Path(path).exists():
        raise FileNotFoundError(
            f"Vector store not found at {path}. Run `python scripts/ingest.py` first."
        )

    embedding = get_embedding_function()
    return Chroma(
        persist_directory=path,
        embedding_function=embedding,
    )


def vectorstore_count(vectorstore: Chroma) -> int:
    """Return the number of documents stored in the vector store."""
    return vectorstore._collection.count()


def _clean_persist_dir(path: str) -> None:
    """Remove a stale Chroma DB so rebuilds don't duplicate documents."""
    p = Path(path)
    if p.exists():
        import shutil

        shutil.rmtree(p, ignore_errors=True)
    p.mkdir(parents=True, exist_ok=True)