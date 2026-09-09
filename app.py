import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import streamlit as st

from findoc.comparison import compare_documents
from findoc.config import get_config
from findoc.errors import FinDocError
from findoc.logging_config import setup_logging
from findoc.pipeline import ask

setup_logging()

st.set_page_config(
    page_title="FinDoc AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

config = get_config()

st.title("FinDoc AI")
st.caption("Ask questions about SEC 10-K filings, with citations.")


def available_tickers():
    from findoc.pipeline import _get_vectorstore
    from findoc.retrieval import retrieve_tickers

    store = _get_vectorstore()
    return retrieve_tickers(store)


def render_citations(citations):
    if not citations:
        return
    with st.expander(f"Sources ({len(citations)})", expanded=False):
        for i, c in enumerate(citations, start=1):
            ticker = c.get("ticker", "?")
            section = c.get("section", "?")
            source = c.get("source", "")
            snippet = (c.get("snippet") or "").strip()
            idx = c.get("index", i)
            st.markdown(
                f"**[{idx}]** `{ticker}` — {section}"
                + (f"\n\n> {snippet}" if snippet else "")
            )
            if source:
                st.caption(f"Source: {Path(source).name}")
            st.divider()


def render_message(msg, show_sources):
    role = msg["role"]
    with st.chat_message(role):
        result = msg.get("result")
        if result is not None:
            st.markdown(result.answer)
            if show_sources:
                render_citations(result.citations)
        else:
            st.markdown(msg["content"])


def render_compare(result):
    st.subheader("Synthesis")
    st.markdown(result.synthesis or "_No synthesis generated._")
    st.divider()

    for ticker, per_answer in result.per_company.items():
        with st.expander(f"**{ticker}** — {per_answer.query}", expanded=True):
            st.markdown(per_answer.answer)
            render_citations(per_answer.citations)


with st.sidebar:
    st.header("Controls")
    tickers = available_tickers() or ["AAPL", "AMZN", "MSFT"]
    selected = st.multiselect(
        "Companies",
        options=tickers,
        default=[],
        help="Leave empty to search all companies.",
    )
    k = st.slider("Context chunks (k)", min_value=1, max_value=10, value=config.top_k)
    show_sources = st.checkbox("Show sources", value=True)
    if st.button("Clear history"):
        st.session_state.messages = []

tab_ask, tab_compare = st.tabs(["Ask", "Compare"])

with tab_ask:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        render_message(msg, show_sources)

    prompt = st.chat_input("Ask a question about the filings...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        ticker_filter = selected[0] if len(selected) == 1 else None
        with st.chat_message("assistant"):
            try:
                with st.spinner("Searching filings and generating answer..."):
                    result = ask(prompt, ticker_filter=ticker_filter, k=k)
            except FinDocError as exc:
                st.error(str(exc))
                st.session_state.messages.append(
                    {"role": "assistant", "content": f"⚠️ {exc}"}
                )
            else:
                st.markdown(result.answer)
                if show_sources:
                    render_citations(result.citations)
                st.session_state.messages.append(
                    {"role": "assistant", "result": result}
                )

with tab_compare:
    st.markdown(
        "Compare how multiple companies' 10-K filings address the same question."
    )
    cmp_tickers = st.multiselect(
        "Companies to compare",
        options=tickers,
        default=tickers[:2],
        help="Select at least two companies.",
    )
    cmp_k = st.slider(
        "Context chunks per company",
        min_value=1,
        max_value=10,
        value=config.top_k,
        key="cmp_k",
    )
    cmp_prompt = st.text_input(
        "Comparison question",
        placeholder="e.g. What are the main supply chain risks?",
    )
    cmp_go = st.button("Compare", type="primary")

    if cmp_go:
        if not cmp_prompt.strip():
            st.warning("Enter a comparison question first.")
        elif len(cmp_tickers) < 2:
            st.warning("Select at least two companies to compare.")
        else:
            try:
                with st.spinner("Retrieving per-company findings and synthesizing..."):
                    st.session_state.compare_result = compare_documents(
                        cmp_prompt.strip(), cmp_tickers
                    )
            except FinDocError as exc:
                st.error(str(exc))

    if "compare_result" in st.session_state and cmp_go:
        render_compare(st.session_state.compare_result)