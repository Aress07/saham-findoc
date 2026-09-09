# FinDoc AI — Knowledge to Learn Before Coding

A reference guide covering everything you should understand conceptually before writing code for the RAG-based financial document assistant. Work through this roughly in order — each section builds on the last.

---

## 1. Python & Environment Fundamentals

You don't need to be an expert, but be comfortable with:

- **Virtual environments** (`venv` or `conda`) — every AI project needs isolated dependencies
- **Environment variables** for API keys (`.env` files, `python-dotenv`) — never hardcode API keys
- **`pip` / `requirements.txt`** — pinning versions matters, LangChain breaks between versions often
- **Async basics** (`async`/`await`) — many LLM API calls and Streamlit apps use this
- **JSON handling** — LLM responses, config files, and API payloads are almost all JSON

---

## 2. What is RAG (Retrieval-Augmented Generation)?

**The core idea:** instead of asking an LLM a question directly (where it can hallucinate or lack knowledge of your specific documents), you:

1. Retrieve relevant chunks of text from your own document collection
2. Insert those chunks into the prompt as context
3. Ask the LLM to answer _using only that context_

**Why it matters for finance:** LLMs are not reliable on specific numbers, dates, or clauses from documents they weren't trained on (or were trained on long ago). RAG grounds answers in real, verifiable source text — critical when wrong financial information has real consequences.

**Key concept to internalize:** RAG doesn't make the LLM "smarter" — it changes _what information_ the LLM has access to at answer-time. The quality of your retrieval step is usually the bottleneck, not the LLM itself.

---

## 3. Embeddings

**What they are:** a way to convert text into a list of numbers (a vector) such that semantically similar text produces similar vectors.

You need to understand:

- **Why we use them:** to measure "closeness in meaning" between a user's question and chunks of your documents, so you can retrieve relevant ones
- **Cosine similarity** — the standard way to measure how close two vectors are
- **Embedding models differ** — OpenAI's `text-embedding-3-small`, or free local options via `sentence-transformers` (e.g. `all-MiniLM-L6-v2`). Know the tradeoff: API-based embeddings cost money and require network calls; local models are free but need more setup and are usually lower quality.
- **Dimensionality** — embeddings are vectors of fixed length (e.g. 384, 1536 dims). This matters when setting up your vector database schema.

---

## 4. Vector Databases

**What they do:** store embeddings + their original text, and let you query "find me the N most similar chunks to this query vector" efficiently.

Concepts to know before touching code:

- **Chroma** — the one you'll likely use: free, runs locally, simple Python API, good for a portfolio project
- **FAISS** — a lower-level library for vector search (Chroma often uses this under the hood)
- **Indexing** — how a vector DB organizes vectors for fast search (you don't need deep algorithm knowledge, but know that "index" here ≠ database index in the SQL sense)
- **Metadata filtering** — being able to query "only search chunks from Bank X's 2025 filing" — you'll need this for the multi-document comparison feature
- **Persistence** — Chroma can save to disk so you don't re-embed documents every run

---

## 5. Document Parsing & Chunking

This is the least glamorous part of RAG and the part that determines quality the most.

**Parsing:**

- 10-K filings are long, messy documents (HTML or PDF) full of tables, footnotes, and boilerplate legal language
- Libraries: `unstructured`, `pdfplumber`, or `BeautifulSoup` if working with the HTML versions from SEC EDGAR
- Know the difference between extracting **raw text** vs. preserving **structure** (headers, sections, tables) — structure matters a lot for financial documents

**Chunking:**

- **Fixed-size chunking** (e.g. every 500 tokens) — simple but can cut sentences/tables in half
- **Semantic/structural chunking** — splitting by section (e.g. "Item 1A: Risk Factors", "Item 7: MD&A") — much better for 10-Ks since they have a legally mandated structure
- **Chunk overlap** — why chunks usually overlap slightly (so context isn't lost at boundaries)
- **Chunk size tradeoffs** — smaller chunks = more precise retrieval but less context; larger chunks = more context but noisier retrieval

**Concept to understand:** the SEC requires 10-Ks to follow a standard structure (Items 1 through 15). Knowing this structure in advance lets you chunk intelligently instead of blindly.

---

## 6. Retrieval Strategies

- **Top-k retrieval** — the basic approach: get the k most similar chunks to a query
- **Re-ranking** — an optional second pass (e.g. using Cohere's rerank API) that re-scores retrieved chunks for relevance, often improving quality significantly
- **Hybrid search** — combining keyword search (BM25) with vector search — useful because pure embeddings can miss exact terms like ticker symbols or specific dollar figures
- **Multi-query / query expansion** — reformulating the user's question into multiple search queries to improve recall (relevant for your "compare bank A vs bank B" feature)

---

## 7. LLM APIs & Prompt Engineering

- **How to call an LLM API** (Claude or OpenAI) — request/response structure, system vs. user messages, tokens, temperature
- **Context window** — the max amount of text (prompt + retrieved chunks + conversation history) the model can process at once
- **Prompt engineering for RAG specifically:**
    - Instructing the model to answer _only_ from provided context
    - Instructing it to say "I don't know" when the context doesn't contain the answer (critical for reducing hallucination)
    - Asking for citations/source attribution in the output format
- **Token costs** — understand that longer context = more cost per call; this affects chunk size and top-k decisions

---

## 8. LangChain (or LlamaIndex) Basics

Pick one framework — LangChain is more common in job postings. Understand these building blocks before coding:

- **Document loaders** — ingesting files into a standard format
- **Text splitters** — the chunking utilities
- **Vector store integrations** — how LangChain talks to Chroma
- **Retrievers** — the abstraction that wraps "search the vector store"
- **Chains** — the pipeline that connects retrieval → prompt construction → LLM call
- **Memory** (optional) — if you want multi-turn conversation instead of single Q&A

You don't need to memorize the API — just understand the _pipeline shape_ so the code makes sense when you write it: **Load → Split → Embed → Store → Retrieve → Generate**.

---

## 9. Evaluation for RAG Systems

This is the part that makes your project look like engineering, not a tutorial. Know these concepts:

- **Retrieval accuracy** — did the system retrieve the chunk(s) that actually contain the answer?
- **Faithfulness / groundedness** — does the generated answer actually match what's in the retrieved context (vs. the model making things up anyway)?
- **Answer relevance** — does the answer address the actual question asked?
- **Building a test set** — write ~15-20 question/answer pairs yourself, with the correct source cited, before you start evaluating
- **Manual grading is fine** for a portfolio project — you don't need a fully automated eval framework, but you do need _some_ systematic check, not just "it seemed to work when I tried it"

---

## 10. Domain Knowledge: Reading a 10-K

You don't need to be a financial analyst, but know the basic structure so your chunking and test questions make sense:

- **Item 1** — Business description
- **Item 1A** — Risk Factors (usually the longest, densest section — good for testing retrieval)
- **Item 7** — Management's Discussion & Analysis (MD&A) — narrative explanation of financial performance
- **Item 8** — Financial Statements (balance sheet, income statement, cash flow statement)
- Know that different banks structure their risk factors differently, which is exactly why "compare risk factors across banks" is a good stress-test for your retrieval system

---

## 11. Deployment Basics

- **Streamlit** — the fastest way to wrap a Python script in a usable web UI (text input, chat display, file upload)
- **Hugging Face Spaces / Render free tier** — where to host it so you have a live demo link, not just code
- **Secrets management in deployment** — how to keep your API key safe when the app is public (never commit `.env` files to GitHub)
- **Basic error handling** — what happens when the API times out, or a query returns no relevant chunks — plan for this before demoing

---

## 12. Nice-to-Know (Stretch Concepts)

Not required to start, but good to be aware of since they may come up in interviews:

- **Agents** — LLMs that can decide which tool/action to take (a step beyond plain RAG)
- **MLOps basics** — Docker, CI/CD — relevant since job postings frequently mention these even for AI Engineer roles
- **Cost/latency monitoring** — tracking how much each query costs and how long it takes, since production LLM systems care about both

---

## Suggested Order to Learn This

1. RAG concept (Section 2) — understand the "why" first
2. Embeddings + vector DBs (Sections 3-4) — the retrieval half
3. Chunking + parsing (Section 5) — apply it to real 10-K structure (Section 10)
4. LLM APIs + prompting (Section 7)
5. LangChain pipeline shape (Section 8) — now the framework will make sense
6. Retrieval strategies (Section 6) — improve what you built
7. Evaluation (Section 9) — prove it works
8. Deployment (Section 11) — ship it

Once you've skimmed all of this, you'll understand _why_ each line of code exists rather than copy-pasting a tutorial — which is the actual goal.