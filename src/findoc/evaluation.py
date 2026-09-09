from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from findoc.comparison import compare_documents
from findoc.pipeline import ask
from findoc.retrieval import retrieve_tickers
from findoc.vectorstore import load_vectorstore


_COMPANY_NAMES = {
    "AAPL": ("apple",),
    "AMZN": ("amazon",),
    "MSFT": ("microsoft",),
}


def _is_comparison(item: dict, tickers: list[str]) -> bool:
    """A comparison question: answerable, no single ticker, involves 2+ companies."""
    expected_section = item.get("expected_source_section", "")
    ticker = item.get("ticker", "")
    if not expected_section or ticker:
        return False
    question = item.get("question", "").lower()
    if any(w in question for w in ("compare", " vs ", "versus", "difference")):
        return True
    mentioned = 0
    for t in tickers:
        names = _COMPANY_NAMES.get(t, (t.lower(),))
        if any(n in question for n in names):
            mentioned += 1
    return mentioned >= 2


@dataclass
class EvalItemResult:
    question: str
    expected_section: str
    ticker: str
    expected_decline: bool
    answer: str = ""
    cited_sections: list[str] = field(default_factory=list)
    has_citations: bool = False
    section_match: bool = False
    declined_correctly: bool = False
    declined_incorrectly: bool = False
    passed: bool = False
    latency_s: float = 0.0


def load_test_set(path: str | Path) -> list[dict]:
    items = []
    p = Path(path)
    for line in p.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        item = json.loads(stripped)
        items.append(item)
    return items


def _is_decline(expected_summary: str) -> bool:
    return expected_summary.strip().upper().startswith("SHOULD DECLINE")


def _section_matches(cited_sections: list[str], expected: str) -> bool:
    """Check if any cited section overlaps with the expected section number."""
    if not expected:
        return False
    expected_norm = expected.lower().strip()
    for sec in cited_sections:
        sec_norm = sec.lower()
        if expected_norm in sec_norm or sec_norm in expected_norm:
            return True
    return False


def _decline_phrase() -> str:
    return "don't have this information in the provided documents"


def _is_pure_decline(answer: str) -> bool:
    """True only if the answer is essentially just the decline statement."""
    phrase = _decline_phrase()
    if phrase not in answer.lower():
        return False
    # Allow the phrasing plus a small amount of wrapper text, but not a
    # substantial answer (which may briefly note missing info mid-answer).
    return len(answer.strip()) < len(phrase) * 3


def evaluate_item(item: dict, ticker_filter: str | None = None) -> EvalItemResult:
    question = item["question"]
    expected_summary = item.get("expected_answer_summary", "")
    expected_section = item.get("expected_source_section", "")
    ticker = item.get("ticker", "")
    expected_decline = _is_decline(expected_summary)

    t0 = time.time()
    vs = load_vectorstore()
    tickers = retrieve_tickers(vs)
    if _is_comparison(item, tickers):
        comp = compare_documents(question, tickers)
        answer = comp.synthesis
        cited_sections = [
            c["section"] for r in comp.per_company.values() for c in r.citations
        ]
    else:
        result = ask(question, ticker_filter=ticker_filter or (ticker or None))
        answer = result.answer
        cited_sections = [c["section"] for c in result.citations]
    elapsed = time.time() - t0

    has_citations = bool(cited_sections)

    item_result = EvalItemResult(
        question=question,
        expected_section=expected_section,
        ticker=ticker,
        expected_decline=expected_decline,
        answer=answer,
        cited_sections=cited_sections,
        has_citations=has_citations,
        latency_s=round(elapsed, 1),
    )

    declined_now = _is_pure_decline(answer)

    if expected_decline:
        item_result.declined_correctly = declined_now
        item_result.declined_incorrectly = not declined_now
        item_result.passed = declined_now
    else:
        item_result.section_match = _section_matches(cited_sections, expected_section)
        # Pass if we have citations AND (we declined-but-improperly OR section matches)
        if declined_now:
            item_result.passed = False
        else:
            item_result.passed = has_citations and (
                item_result.section_match or not expected_section
            )

    return item_result


def run_evaluation(
    test_set_path: str | Path,
    throttle_s: float = 3.0,
) -> list[EvalItemResult]:
    """Run the full test set with a throttle between Groq calls."""
    items = load_test_set(test_set_path)
    results: list[EvalItemResult] = []

    for i, item in enumerate(items, start=1):
        print(f"  [{i}/{len(items)}] {item['question'][:60]}...")
        try:
            res = evaluate_item(item)
        except Exception as e:
            print(f"      ERROR: {e}")
            res = EvalItemResult(
                question=item["question"],
                expected_section=item.get("expected_source_section", ""),
                ticker=item.get("ticker", ""),
                expected_decline=item.get("expected_answer_summary", "").strip().upper().startswith("SHOULD DECLINE"),
            )
        results.append(res)
        if i < len(items):
            time.sleep(throttle_s)

    return results


def summarize(
    results: list[EvalItemResult],
    output_path: str | Path,
    test_set_path: str | Path,
) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    declined_count = sum(1 for r in results if r.expected_decline)
    declined_correct = sum(1 for r in results if r.expected_decline and r.declined_correctly)

    answerable = [r for r in results if not r.expected_decline]
    ans_total = len(answerable)
    ans_passed = sum(1 for r in answerable if r.passed)
    citation_rate = (
        sum(1 for r in answerable if r.has_citations) / ans_total if ans_total else 0.0
    )
    section_accuracy = (
        sum(1 for r in answerable if r.section_match) / ans_total if ans_total else 0.0
    )
    avg_latency = (
        sum(r.latency_s for r in results) / total if total else 0.0
    )

    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "question",
                "ticker",
                "expected_section",
                "expected_decline",
                "passed",
                "has_citations",
                "section_match",
                "declined_correctly",
                "cited_sections",
                "latency_s",
                "answer",
            ]
        )
        for r in results:
            writer.writerow(
                [
                    r.question,
                    r.ticker,
                    r.expected_section,
                    r.expected_decline,
                    r.passed,
                    r.has_citations,
                    r.section_match,
                    r.declined_correctly,
                    "|".join(r.cited_sections),
                    r.latency_s,
                    r.answer,
                ]
            )

    summary = {
        "test_set": str(test_set_path),
        "total": total,
        "passed": passed,
        "overall_pass_rate": round(passed / total, 3) if total else 0.0,
        "answerable_total": ans_total,
        "answerable_passed": ans_passed,
        "answerable_pass_rate": round(ans_passed / ans_total, 3) if ans_total else 0.0,
        "citation_presence_rate": round(citation_rate, 3),
        "section_match_accuracy": round(section_accuracy, 3),
        "decline_count": declined_count,
        "decline_correct": declined_correct,
        "decline_accuracy": round(declined_correct / declined_count, 3) if declined_count else 0.0,
        "avg_latency_s": round(avg_latency, 1),
        "results_file": str(output_path),
    }
    return summary