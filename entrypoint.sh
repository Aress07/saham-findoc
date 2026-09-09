#!/usr/bin/env sh
# Container entrypoint: ensure raw filings + vector store exist, then serve.
set -e
cd /app

if [ ! -f data/raw/MSFT_10K.htm ]; then
  echo "=== Downloading sample filings ==="
  python scripts/download_sample_filings.py
fi

if [ ! -d data/processed/chroma_db ]; then
  echo "=== Building vector store ==="
  python scripts/ingest.py
fi

echo "=== Vector store ready: $(ls data/processed/chroma_db | wc -l) files ==="
exec streamlit run app.py --server.port="${PORT:-8501}" --server.address=0.0.0.0