"""
evaluate_real_bugs.py

Runs the agent against the "real bugs" benchmark tier — 3 genuine
historical bugs sourced from real, still-used open-source Python
libraries (humanize), each verified to reproduce exactly as it did in
real history, and each resolved by the actual historical fix commit.

This complements evaluate.py (the 5 self-authored bugs): that tier
proves the loop works end-to-end on controlled, simple cases; this
tier tests it against real mistakes real developers made.

Sources (for citation in your report):
- bug1: humanize commit 2f179b6 — "Fix: AP style for 0 is 'zero'"
- bug2: humanize commit 818c9b3 — "fixed intword returning 1000.0
  million instead of 1.0 billion" (rounding edge case)
- bug3: humanize commit db96782 — "Show more than bytes for negative
  file sizes"
"""

import sys

from evaluate import BenchmarkCase, run_benchmark, print_summary


if __name__ == "__main__":
    # Usage: python evaluate_real_bugs.py <real_bugs_folder>
    # e.g.:  python evaluate_real_bugs.py sandbox\real-bugs-benchmark
    if len(sys.argv) != 2:
        print("Usage: python evaluate_real_bugs.py <real_bugs_folder>")
        sys.exit(1)

    root = sys.argv[1]

    cases = [
        BenchmarkCase(
            "real_bug_1_apnumber_zero",
            f"{root}\\bug1-apnumber",
            f"{root}\\bug1-apnumber\\humanize_mini\\bug_apnumber.py",
            "tests/test_apnumber.py::test_apnumber_zero",
        ),
        BenchmarkCase(
            "real_bug_2_intword_rounding",
            f"{root}\\bug2-intword",
            f"{root}\\bug2-intword\\humanize_mini2\\bug_intword.py",
            "tests/test_intword.py::test_intword_rounds_up_to_next_unit",
        ),
        BenchmarkCase(
            "real_bug_3_naturalsize_negative",
            f"{root}\\bug3-naturalsize",
            f"{root}\\bug3-naturalsize\\humanize_mini3\\bug_naturalsize.py",
            "tests/test_naturalsize.py::test_naturalsize_negative_case",
        ),
    ]

    results = run_benchmark(cases)
    print_summary(results)
