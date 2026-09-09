from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_load_dotenv_done = False


def _ensure_dotenv() -> None:
    global _load_dotenv_done
    if not _load_dotenv_done:
        load_dotenv(_PROJECT_ROOT / ".env")
        _load_dotenv_done = True


@dataclass(frozen=True)
class Config:
    groq_api_key: str = ""
    embedding_provider: str = "local"
    llm_model: str = "openai/gpt-oss-120b"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    vector_store_path: str = "data/processed/chroma_db"
    top_k: int = 5
    log_file: str = "logs/findoc.log"
    log_level: str = "INFO"


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is not None:
        return _config

    _ensure_dotenv()

    _config = Config(
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "local"),
        llm_model=os.getenv("LLM_MODEL", "openai/gpt-oss-120b"),
        chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
        vector_store_path=os.getenv("VECTOR_STORE_PATH", "data/processed/chroma_db"),
        top_k=int(os.getenv("TOP_K", "5")),
        log_file=os.getenv("LOG_FILE", "logs/findoc.log"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
    return _config
