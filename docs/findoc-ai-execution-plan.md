# FinDoc AI — Execution Plan (Zero → Deployed RAG App)

**How to use this plan with opencode/Claude:** Paste one step at a time as an instruction. Do not proceed to the next step until the "Done Criteria" and "Sanity Check" for the current step both pass. Steps are strictly ordered — no step depends on a *later* step's output.

Legend for complexity: 🟢 Low (15–30 min) · 🟡 Medium (30–90 min) · 🔴 High (90+ min)

---

## Phase 0 — Foundation

### Step 1: Repo scaffolding and Python environment
**Build:**
- `requirements.txt` (pin: `langchain`, `langchain-community`, `langchain-openai`, `chromadb`, `streamlit`, `python-dotenv`, `pypdf`, `tiktoken`, `pandas`, `pytest`)
- `.gitignore` (venv, `__pycache__`, `.env`, `chroma_db/`, `.streamlit/secrets.toml`)
- `.env.example` (`OPENAI_API_KEY=`, `EMBEDDING_PROVIDER=`, `LLM_MODEL=`)
- Folder structure: `src/findoc/`, `src/findoc/__init__.py`, `data/raw/`, `data/processed/`, `tests/`, `scripts/`
- `README.md` (title + one-paragraph description only, will expand later)

**Verification:** `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` completes with no errors.
**Dependencies:** None.
**Sanity check:** `python -c "import langchain, chromadb, streamlit; print('ok')"` prints `ok`.
**Complexity:** 🟢 Low

---

### Step 2: Config module
**Build:**
- `src/findoc/config.py` — a `Config` dataclass/pydantic model that loads from `.env` (embedding provider, LLM model name, chunk size, chunk overlap, vector store path, top-k retrieval count). Include a `get_config()` singleton loader using `python-dotenv`.

**Verification:** Import and instantiate config with a test `.env`; all fields populate with correct types and sane defaults when `.env` is absent.
**Dependencies:** Step 1.
**Sanity check:** `python -c "from findoc.config import get_config; print(get_config())"` prints populated config with no exceptions.
**Complexity:** 🟢 Low

---

## Phase 1 — Data Layer

### Step 3: Acquire sample 10-K documents
**Build:**
- `scripts/download_sample_filings.py` — downloads 3–5 real 10-K filings (e.g., via SEC EDGAR full-text search/API, plain HTML or TXT format) into `data/raw/{TICKER}_10K_{YEAR}.txt` or `.htm`. Include a hardcoded list of 3-5 tickers/URLs (e.g., AAPL, MSFT, TSLA) with EDGAR filing URLs.
- `data/raw/README.md` documenting source, ticker, fiscal year, and filing date for each file.

**Verification:** `data/raw/` contains 3+ real filings, each >100KB, human-readable text with visible section headers like "Item 1. Business", "Item 1A. Risk Factors", "Item 7. Management's Discussion".
**Dependencies:** Step 1.
**Sanity check:** `ls -la data/raw/ && head -c 500 data/raw/*.txt` (or `.htm`) shows real financial filing content, not HTML error pages.
**Complexity:** 🟡 Medium (SEC rate limits / User-Agent headers required)

---

### Step 4: Document loader
**Build:**
- `src/findoc/loaders.py` — `load_10k(filepath: str) -> Document` (LangChain `Document` with `page_content` and `metadata={"source", "ticker", "fiscal_year"}`). Support both `.txt` and `.htm` (strip HTML tags, keep text).
- `tests/test_loaders.py` — loads each sample file, asserts non-empty content and correct metadata.

**Verification:** All files in `data/raw/` load without exceptions; metadata correctly extracted from filename.
**Dependencies:** Step 3.
**Sanity check:** `pytest tests/test_loaders.py -v` — all tests pass.
**Complexity:** 🟢 Low

---

### Step 5: Structural chunker (10-K section-aware splitting)
**Build:**
- `src/findoc/chunking.py` — `structural_split(document: Document) -> list[Document]`. Detects standard 10-K "Item N" section headers via regex, splits into section-level chunks first, then applies `RecursiveCharacterTextSplitter` within oversized sections (using chunk_size/overlap from config). Each output chunk's metadata must include `section` (e.g., "Item 1A. Risk Factors"), `source`, `ticker`, `fiscal_year`, `chunk_id`.
- `tests/test_chunking.py` — verifies section detection on a sample filing and correct metadata propagation.

**Verification:** Chunking a full 10-K produces chunks each tagged with the correct `Item` section; no chunk exceeds max size; no content lost (spot-check reconstructed length vs original).
**Dependencies:** Step 4.
**Sanity check:** `pytest tests/test_chunking.py -v` passes; `python -c "from findoc.loaders import load_10k; from findoc.chunking import structural_split; d=load_10k('data/raw/<file>'); c=structural_split(d); print(len(c), c[0].metadata)"` shows a nonzero chunk count with populated section metadata.
**Complexity:** 🟡 Medium

---

## Phase 2 — Embedding & Storage

### Step 6: Embedding module
**Build:**
- `src/findoc/embeddings.py` — `get_embedding_function()` returning either `OpenAIEmbeddings` or a local `HuggingFaceEmbeddings` (e.g., `sentence-transformers/all-MiniLM-L6-v2`) based on `Config.embedding_provider`.

**Verification:** Function returns a working embedding object for both providers (test with a dummy `.env` value for each); embedding a short string returns a vector of expected dimensionality.
**Dependencies:** Step 2.
**Sanity check:** `python -c "from findoc.embeddings import get_embedding_function; e=get_embedding_function(); v=e.embed_query('test'); print(len(v))"` prints a vector length > 0.
**Complexity:** 🟡 Medium (API key handling, optional local model download)

---

### Step 7: Vector store ingestion pipeline
**Build:**
- `src/findoc/vectorstore.py` — `build_vectorstore(documents: list[Document], persist_dir: str) -> Chroma` and `load_vectorstore(persist_dir: str) -> Chroma`.
- `scripts/ingest.py` — CLI script: loads all files in `data/raw/`, chunks each via `structural_split`, embeds, and persists to `data/processed/chroma_db/`. Prints ingestion summary (docs processed, chunks created, time taken).

**Verification:** Running ingestion creates a populated Chroma DB on disk; reloading it returns the same document count.
**Dependencies:** Steps 5, 6.
**Sanity check:** `python scripts/ingest.py && python -c "from findoc.vectorstore import load_vectorstore; vs=load_vectorstore('data/processed/chroma_db'); print(vs._collection.count())"` prints a count matching the number of chunks from Step 5.
**Complexity:** 🟡 Medium

---

### Step 8: Retrieval module
**Build:**
- `src/findoc/retrieval.py` — `retrieve(query: str, vectorstore, k: int, filters: dict | None = None) -> list[Document]`. Support optional metadata filtering (e.g., by `ticker` or `section`) for later multi-doc comparison.
- `tests/test_retrieval.py` — asserts top-k results are relevant (e.g., query "risk factors" returns chunks tagged `Item 1A`).

**Verification:** Retrieval for a known query returns semantically relevant chunks with correct metadata; filtering by ticker only returns that ticker's chunks.
**Dependencies:** Step 7.
**Sanity check:** `pytest tests/test_retrieval.py -v` passes.
**Complexity:** 🟡 Medium

---

## Phase 3 — Generation & Grounding

### Step 9: Constrained prompt template
**Build:**
- `src/findoc/prompts.py` — `RAG_SYSTEM_PROMPT` and `build_prompt(query: str, chunks: list[Document]) -> str` (or LangChain `ChatPromptTemplate`). Prompt must instruct: answer only from provided context, cite source/section per claim, explicitly say "not found in the provided documents" when context is insufficient. Numbers each context chunk (`[1]`, `[2]`...) for citation mapping.

**Verification:** Manually inspect rendered prompt output for a sample query+chunks — context is clearly delimited, numbered, and instructions are unambiguous.
**Dependencies:** Step 8.
**Sanity check:** `python -c "from findoc.prompts import build_prompt; print(build_prompt('test query', []))"` renders without error and includes the constrained-answering instruction text.
**Complexity:** 🟢 Low

---

### Step 10: LLM generation module with citations
**Build:**
- `src/findoc/generation.py` — `generate_answer(query: str, chunks: list[Document], llm=None) -> AnswerResult` where `AnswerResult` is a dataclass with `answer: str`, `citations: list[dict]` (mapping `[n]` markers back to `{source, ticker, section}`). Calls `ChatOpenAI` (or configurable LLM) with the Step 9 prompt.

**Verification:** For a factual query against ingested filings, returned answer contains inline citation markers matching real source chunks; for an out-of-scope query, model correctly declines.
**Dependencies:** Steps 8, 9.
**Sanity check:** `python -c "from findoc.pipeline import ask; print(ask('What are Apple's main risk factors?'))"` (after Step 11) — or directly test `generate_answer` with retrieved chunks — prints an answer with numbered citations resolvable to real filing sections.
**Complexity:** 🔴 High (prompt tuning, citation parsing reliability)

---

### Step 11: End-to-end pipeline orchestration
**Build:**
- `src/findoc/pipeline.py` — `ask(query: str, ticker_filter: str | None = None) -> AnswerResult`. Wires together: load vectorstore → retrieve → generate_answer. Single public entrypoint for both CLI and UI.
- `scripts/query_cli.py` — simple CLI: `python scripts/query_cli.py "your question"` prints answer + citations.

**Verification:** Running several test questions against the CLI returns grounded, cited answers end-to-end.
**Dependencies:** Steps 7, 8, 9, 10.
**Sanity check:** `python scripts/query_cli.py "What is Tesla's revenue recognition policy?"` returns a coherent cited answer within a reasonable time (<15s).
**Complexity:** 🟡 Medium

---

## Phase 4 — Multi-Document Comparison

### Step 12: Multi-document comparison logic
**Build:**
- `src/findoc/comparison.py` — `compare_documents(query: str, tickers: list[str]) -> ComparisonResult`. Retrieves relevant chunks per ticker separately (using the Step 8 filter), generates a per-company answer, then a synthesized comparison summary highlighting differences. Reuses `generation.py`.

**Verification:** Query like "Compare risk factors between AAPL and TSLA" returns a structured result with per-company findings and a synthesis, each still citation-backed.
**Dependencies:** Steps 8, 10, 11.
**Sanity check:** `python -c "from findoc.comparison import compare_documents; r=compare_documents('compare liquidity risk', ['AAPL','TSLA']); print(r)"` shows distinct per-ticker sections plus a comparison summary.
**Complexity:** 🔴 High

---

## Phase 5 — Evaluation

### Step 13: Evaluation test set
**Build:**
- `data/eval/test_set.jsonl` — 15–25 hand-written Q&A pairs against the ingested filings: `{"question": ..., "expected_answer_summary": ..., "expected_source_section": ..., "ticker": ...}`. Include a mix of factual, comparison, and "should decline" (unanswerable) questions.

**Verification:** Every question is answerable (or correctly unanswerable) by manually checking the source filings; file is valid JSONL.
**Dependencies:** Step 3.
**Sanity check:** `python -c "import json; [json.loads(l) for l in open('data/eval/test_set.jsonl')]; print('valid jsonl')"` prints without error.
**Complexity:** 🟡 Medium (manual authoring effort)

---

### Step 14: Evaluation harness
**Build:**
- `src/findoc/evaluation.py` — runs each test set item through `pipeline.ask`, computes: citation-presence rate, keyword/section-match against `expected_source_section`, and (optional) LLM-as-judge groundedness score.
- `scripts/run_eval.py` — runs full eval, writes `data/eval/results_{timestamp}.csv` and prints summary metrics.

**Verification:** Eval run completes for all test items and produces a results file with per-question pass/fail and an aggregate score.
**Dependencies:** Steps 11, 13.
**Sanity check:** `python scripts/run_eval.py` completes and prints an overall groundedness/citation accuracy percentage.
**Complexity:** 🟡 Medium

---

## Phase 6 — UI

### Step 15: Streamlit app — basic Q&A
**Build:**
- `app.py` — Streamlit app: text input for query, ticker multi-select (populated from ingested docs), "Ask" button calling `pipeline.ask`, displays answer text.

**Verification:** App launches locally, accepts a question, and displays a grounded answer.
**Dependencies:** Step 11.
**Sanity check:** `streamlit run app.py` starts without errors; manually asking a question in the browser returns an answer.
**Complexity:** 🟢 Low

---

### Step 16: Streamlit UI — citations display
**Build:** Update `app.py` — render citations as expandable source cards below the answer (section name, ticker, snippet excerpt) using `AnswerResult.citations`.

**Verification:** Each `[n]` marker in the answer text has a corresponding, correctly matched source card.
**Dependencies:** Step 15, Step 10.
**Sanity check:** Manual browser check — clicking a citation expander shows the actual filing excerpt referenced.
**Complexity:** 🟢 Low

---

### Step 17: Streamlit UI — multi-document comparison view
**Build:** Add a "Compare" tab/mode in `app.py` using `st.tabs` — select 2+ tickers, calls `comparison.compare_documents`, renders per-company columns + synthesis section with citations.

**Verification:** Comparison mode works end-to-end in-browser for at least one query across 2 tickers.
**Dependencies:** Steps 12, 16.
**Sanity check:** Manual browser test of comparison tab produces a readable, cited side-by-side result.
**Complexity:** 🟡 Medium

---

## Phase 7 — Hardening & Deployment

### Step 18: Error handling & logging
**Build:**
- `src/findoc/logging_config.py` — standard logging setup (console + optional file).
- Add try/except with user-friendly error messages in `pipeline.py`, `generation.py`, and `app.py` (e.g., missing API key, empty vector store, LLM timeout).

**Verification:** Deliberately trigger each failure mode (bad API key, empty DB) and confirm friendly error messages, not raw stack traces, in the UI.
**Dependencies:** Steps 11, 15.
**Sanity check:** Temporarily unset `OPENAI_API_KEY` and run `streamlit run app.py`; app shows a clear config error instead of crashing.
**Complexity:** 🟢 Low

---

### Step 19: Packaging for deployment
**Build:**
- Finalize `requirements.txt` with pinned versions (`pip freeze > requirements.txt` cleaned to only real deps).
- `Dockerfile` (Python slim base, copy app, install deps, expose Streamlit port, `CMD streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`).
- `.streamlit/config.toml` (headless=true, theme).
- Ensure `data/processed/chroma_db/` is either committed (small sample) or rebuilt on container start via an `entrypoint.sh` that runs `scripts/ingest.py` if the DB doesn't exist.

**Verification:** `docker build -t findoc-ai .` succeeds; `docker run -p 8501:8501 --env-file .env findoc-ai` serves a working app at `localhost:8501`.
**Dependencies:** Steps 15–18.
**Sanity check:** `curl -I http://localhost:8501` returns HTTP 200 while the container runs.
**Complexity:** 🟡 Medium

---

### Step 20: Deploy to Hugging Face Spaces (or Render)
**Build:**
- `README.md` Spaces metadata header (`sdk: streamlit`, `app_file: app.py`) if using HF Spaces, or `render.yaml` if using Render.
- Push repo to the target platform; configure `OPENAI_API_KEY` as a secret/environment variable in the platform dashboard (never committed).

**Verification:** Public deployed URL loads the app; a live query returns a grounded, cited answer using the deployed vector store.
**Dependencies:** Step 19.
**Sanity check:** Open the deployed URL in an incognito browser window, run one factual query and one comparison query — both succeed.
**Complexity:** 🟡 Medium

---

### Step 21: Final documentation pass
**Build:** Expand `README.md` — architecture diagram (text/mermaid), setup instructions, how to add new filings, eval results summary, known limitations, deployed URL.

**Verification:** A fresh reader could clone the repo and reproduce local setup using only the README.
**Dependencies:** All prior steps.
**Sanity check:** Follow the README's own setup instructions verbatim in a clean clone/venv; app runs successfully.
**Complexity:** 🟢 Low

---

## Summary Dependency Chain

```
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → {12, 13→14, 15→16→17} → 18 → 19 → 20 → 21
```

Total steps: 21 · Estimated total effort: ~3–5 focused working days depending on LLM/API latency and manual eval authoring time.
