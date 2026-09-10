# FinDoc AI — Execution Progress

## Phase 0 — Foundation
- [x] Step 1: Repo scaffolding & Python environment
- [x] Step 2: Config module

## Phase 1 — Data Layer
- [x] Step 3: Acquire sample 10-K documents
- [x] Step 4: Document loader
- [x] Step 5: Structural chunker

## Phase 2 — Embedding & Storage
- [x] Step 6: Embedding module
- [x] Step 7: Vector store ingestion pipeline
- [x] Step 8: Retrieval module

## Phase 3 — Generation & Grounding
- [x] Step 9: Constrained prompt template
- [x] Step 10: LLM generation module with citations
- [x] Step 11: End-to-end pipeline orchestration

## Phase 4 — Multi-Document Comparison
- [x] Step 12: Multi-document comparison logic

## Phase 5 — Evaluation
- [x] Step 13: Evaluation test set
- [x] Step 14: Evaluation harness (`src/findoc/evaluation.py`, `scripts/run_eval.py`)

### Evaluation baseline (20 items, 2026-09-10)
- Overall pass rate: **11/20 (55%)**
- Answerable: 7/16 (43.8%); citation presence 75% (12/16); section-match 43.8% (7/16)
- Should-decline: **4/4 (100%)**
- Avg latency per question: 4.3s
- Diagnosis:
  - Declines on answerable questions (Apple products, Amazon risk factors) — model over-conservative with decline instruction.
  - MSFT section labels coarse/truncated ("ITEM 6. [R", "Preamble") → wrong section-match on correct answers.
  - Comparison items declined when per-company generation declined → synthesis "no findings".
  - Action items for Phase 7 hardening.

## Phase 6 — UI
- [x] Step 15: Streamlit app — basic Q&A (`app.py`: chat input, multi-company filter, k slider, history)
- [x] Step 16: Streamlit UI — citations display (per-answer Sources expander: citation index, ticker, section, snippet, source file; show/hide toggle)
- [x] Step 17: Streamlit UI — multi-document comparison (Compare tab: per-company findings + sources, synthesis summary, validation of ≥2 companies)

## Phase 7 — Hardening & Deployment
- [x] Step 18: Error handling & logging (`errors.py` FinDocError hierarchy; `logging_config.py` console+file; friendly errors in pipeline/generation/app; failures verified — missing key/DB, empty retrieval, LLM failure)
- [x] Step 19: Packaging for deployment (`requirements.txt` pinned; `Dockerfile` python:3.12-slim; `entrypoint.sh` downloads filings + builds vector store when missing; `.streamlit/config.toml` headless+theme; `.dockerignore`). Verified: `docker build -t findoc-ai .` OK; container serves HTTP 200 + `/_stcore/health` 200, rebuilt 1271-chunk store from scratch. Also added `--tickers` arg to download script (default AAPL MSFT AMZN).)
- [ ] Step 20: Deploy — path chosen: **Render** (free). HF Spaces unavailable on free tier (2026: Streamlit Spaces are Docker-backed/paid). `render.yaml` blueprint pushed to GitHub (`e31071c`); awaiting user deploy via Render Blueprint UI + GROQ_API_KEY secret. Alt: `scripts/deploy_hf.py` kept if Pro later.
- [ ] Step 21: Final documentation pass — DEFERRED with Step 20.
