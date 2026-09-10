#!/usr/bin/env sh
# Container entrypoint: verify the prebuilt vector store is present, then serve.
# The vector store is built at CI/dev time and shipped in the image; it is
# intentionally NOT re-ingested here (ingestion exceeds constrained memory).
set -e
cd /app

if [ ! -d data/processed/chroma_db ]; then
  echo "ERROR: vector store missing at data/processed/chroma_db." >&2
  echo "Rebuild it locally with: python scripts/ingest.py" >&2
  exit 1
fi

exec streamlit run app.py --server.port="${PORT:-8501}" --server.address=0.0.0.0