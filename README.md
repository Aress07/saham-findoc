---
title: FinDoc AI
emoji: 📄
colorFrom: green
colorTo: blue
sdk: streamlit
app_file: app.py
pinned: false
---

# FinDoc AI

A RAG-based financial document assistant that answers questions grounded in real
10-K filings with source citations.

**Live: [https://findoc-ai.onrender.com](https://findoc-ai.onrender.com)** (Render, free tier — sleeps after ~15 min idle; first open takes ~2 min to cold-start).

## What it does

- **Ask** — chat with the latest AAPL / MSFT / AMZN 10-K filings. Answers must cite the exact `[n]` sources that support them.
- **Compare** — pick two+ companies and get a synthesis of their results.
- **Declines responsibly** — if the answer isn't in the filings, it says so instead of hallucinating.

## How it works

1. **Ingest**: SEC 10-K HTML filings → structural chunking by section (1,271 chunks).
2. **Embed**: local ONNX model (`fastembed`, `BAAI/bge-small-en-v1.5`, 384-dim) — no GPU/torch needed.
3. **Retrieve**: Chroma vector store → top-k relevant sections per question.
4. **Generate**: Groq (`openai/gpt-oss-120b`, temperature 0.1) with a grounding prompt that requires bracketed citations and a disable-hallucination instruction.

## Tech stack

Python 3.12, Streamlit, LangChain (core/huggingface/chroma/groq), ChromaDB, fastembed (ONNX), BeautifulSoup, Groq API, Docker, Render.

## Run locally

```bash
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
copy .env.example .env    # or create .env with GROQ_API_KEY=gsk_...
python scripts/ingest.py                   # build data/processed/chroma_db
streamlit run app.py
```

(The vector store is already committed, so `ingest.py` is only needed when you add filings.)

## Add or refresh filings

```bash
python scripts/download_sample_filings.py --tickers AAPL MSFT AMZN   # fetch latest 10-Ks
python scripts/ingest.py                                              # rebuild the store
```

## Evaluation

20-question test set (`data/eval/test_set.jsonl`) — baseline 2026-09-10:

- Overall **11/20 (55%)**; answerable 7/16 (43.8%); citation presence 75%
- Should-decline **4/4 (100%)**
- Avg latency ~4.3s; run it yourself with `python scripts/run_eval.py`

### Known limitations

- Model can be over-conservative and decline answerable questions (re-ask if that happens).
- MSFT section labels can be coarse/truncated ("ITEM 6. [R"), which hurts section-match scoring.
- Comparison answers depend on each per-company step succeeding.
- Answers are nondeterministic (LLM temperature 0.1); results vary slightly run-to-run.

## Deployment

- **Host**: Render (free `render.yaml` blueprint → web service).
- **Containers** (`Dockerfile`): `data/processed/chroma_db` and the ONNX model are baked in, so boot only embeds the user's query — peak RAM is ~10% of Render's 512 MB cap (torch was dropped; prior builds OOM'd during in-container ingestion).
- **Secrets**: `GROQ_API_KEY` lives only in your local `.env` and as a Render environment secret + blank (`sync: false`) in `render.yaml`. It is never committed.

## Layout

```
src/findoc/            pipeline, generation, retrieval, comparison, evaluation, vectorstore, chunking, loaders, embeddings, prompts, config, errors, logging
scripts/               ingest.py, run_eval.py, download_sample_filings.py, query_cli.py, deploy_hf.py
app.py                 Streamlit UI (Ask + Compare tabs)
data/eval/             test set + eval results
docs/                  execution plan + progress log
```