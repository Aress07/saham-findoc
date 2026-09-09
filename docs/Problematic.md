# FinDoc AI — The Problem, and Why This Project Solves It

This document explains the _reasoning_ behind the project: what real problem it addresses, why that problem is hard, and how each design choice in the project responds to it. Read this before the technical prep doc — it gives you the "why" that makes the "how" make sense.

---

## 1. The Problematic

### The raw problem

Financial documents — 10-Ks, 10-Qs, prospectuses, loan agreements, compliance policies — are:

- **Extremely long** (a single 10-K can be 100-300 pages)
- **Written in dense legal/financial language**
- **Structurally repetitive but subtly different** across companies (every bank has "Risk Factors," but the actual risks and phrasing differ)
- **Produced constantly** — every public company files quarterly and annually, every bank publishes new policy updates

People who need information from these documents — analysts, compliance officers, risk teams, investors, auditors — currently have two bad options:

1. **Read them manually.** Slow, expensive (analyst time is costly), and error-prone — it's easy to miss a buried clause in page 180.
2. **Ctrl+F / keyword search.** Fast but shallow — keyword search finds where a word appears, not what a section _means_, and it can't answer a question like "what are the main liquidity risks this bank highlights?" unless you already know the right keyword to search.

### Why this is a real (not invented) problem

This is a well-documented pain point in finance: analysts spend a large share of their time on document review rather than judgment/analysis, compliance teams must track subtle year-over-year changes in risk disclosures, and due diligence processes (M&A, lending, audits) require cross-referencing many long documents quickly.

### Why naive AI doesn't fix it

The obvious idea — "just ask ChatGPT about this bank's risks" — fails for a specific reason: **general-purpose LLMs don't know the contents of a specific document you have in mind.** Even if a model was trained on old filings, it:

- Has no guarantee of the correct, current, exact document
- Cannot cite where in the document an answer came from
- Is prone to **hallucination** — confidently stating a number or clause that isn't actually in the source

In finance, a hallucinated number isn't a minor bug — it's the exact failure mode that makes AI dangerous to deploy in this domain without safeguards. This is precisely why banks have been slow and cautious about LLM adoption: correctness and auditability matter more than in most consumer AI use cases.

---

## 2. Reframing the Problem

The real problem isn't "we need an AI that knows about finance." It's narrower and more solvable:

> **We need a system that can answer questions grounded in a specific set of real documents, and show exactly where the answer came from.**

This reframing matters because it turns an open-ended, risky problem ("make the AI knowledgeable and trustworthy in general") into a bounded, engineerable one ("retrieve the right passage, then constrain the model to only use it").

This is the core insight behind **Retrieval-Augmented Generation (RAG)**: separate the _knowledge_ (stored in your document collection) from the _reasoning_ (done by the LLM at query time). The LLM's job shrinks from "know everything" to "read this specific passage and answer accurately" — a much easier and more verifiable task.

---

## 3. How the Project Solves It, Piece by Piece

Each part of the project maps to a specific piece of the problem above:

| Problem                                                                      | Project component                                                                    | How it addresses the problem                                                                                                                                         |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Documents are too long to read entirely for one question                     | **Chunking**                                                                         | Breaks documents into retrievable pieces so only relevant sections are surfaced, not the whole filing                                                                |
| Keyword search misses meaning-based questions                                | **Embeddings + vector search**                                                       | Retrieves passages by _semantic similarity_ to the question, not exact word match — so "liquidity concerns" can match a passage that never uses the word "liquidity" |
| LLMs hallucinate facts not grounded in the source                            | **Constrained prompting** ("answer only from context, say 'I don't know' otherwise") | Forces the model to behave more like a careful reader than a confident guesser                                                                                       |
| No way to verify an AI's answer                                              | **Citations to source document/section**                                             | Makes the system auditable — a human can check the exact passage, which is non-negotiable in finance                                                                 |
| Comparing across companies requires manually reading multiple long documents | **Multi-document retrieval**                                                         | Retrieves relevant passages from several filings at once, so cross-company comparison doesn't require reading each report in full                                    |
| "Does this actually work reliably, or does it just seem to work?"            | **Evaluation with a test set**                                                       | Proves — with evidence, not vibes — how often the system retrieves the right passage and answers faithfully                                                          |
| A working notebook isn't a usable tool                                       | **Deployment (Streamlit + hosting)**                                                 | Turns the pipeline into something a non-technical person could actually query                                                                                        |

---

## 4. Why This Maps to Real Industry Practice

This isn't a toy version of a made-up problem — it mirrors how RAG is actually being adopted in finance and banking right now:

- **Compliance/legal teams** use RAG systems to query policy documents and regulations instead of manual search
- **Equity research and credit analysts** use RAG to accelerate reading through filings for due diligence
- **Customer-facing banking chatbots** use RAG to answer questions about products/terms accurately instead of hallucinating terms and conditions
- **Auditors** use retrieval-grounded tools to trace disclosures back to source documents

Your project is a small, self-contained version of the same architecture used in all of these — which is exactly why it reads as credible to an interviewer rather than as a generic tutorial project.

---

## 5. The Central Tension You're Actually Managing

If you want one sentence to say in an interview that shows you understand the project at a deeper level, it's this:

> **RAG is fundamentally about trading model creativity for model reliability — you deliberately restrict what the LLM is allowed to say, because in finance, a system that says "I don't know" is more valuable than one that always gives a confident-sounding answer.**

Everything in the project — chunking strategy, prompt constraints, evaluation, citations — exists in service of that tradeoff. Once you can explain _that_, you're no longer describing "a chatbot I built," you're describing a design decision you understand the reasoning behind.

---

## 6. Quick Self-Check Before You Start Coding

You're ready to start building once you can answer these in your own words:

1. Why can't you just ask a general LLM directly instead of building RAG?
2. Why is chunking by document structure better than chunking by fixed character count for a 10-K specifically?
3. Why do embeddings retrieve better matches than keyword search for this use case?
4. Why is "I don't know" a _feature_ of your prompt design, not a failure?
5. Why does citation matter more here than in a casual chatbot?

If you can answer all five without looking back at this doc, you understand the project — not just the code.