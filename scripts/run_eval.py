#!/usr/bin/env python3
"""Run the FinDoc evaluation harness.

Usage: python scripts/run_eval.py [--throttle SECONDS]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from findoc.evaluation import run_evaluation, summarize

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_SET = PROJECT_ROOT / "data" / "eval" / "test_set.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the FinDoc evaluation harness")
    parser.add_argument(
        "--throttle",
        type=float,
        default=3.0,
        help="Seconds to wait between Groq calls (rate-limit pacing)",
    )
    args = parser.parse_args()

    if not TEST_SET.exists():
        print(f"ERROR: test set not found at {TEST_SET}")
        sys.exit(1)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_file = PROJECT_ROOT / "data" / "eval" / f"results_{timestamp}.csv"

    print(f"=== FinDoc Evaluation ===\n")
    print(f"Test set: {TEST_SET.name}  (throttle: {args.throttle}s)\n")

    results = run_evaluation(TEST_SET, throttle_s=args.throttle)

    summary = summarize(results, results_file, TEST_SET)

    print("\n=== RESULTS ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()