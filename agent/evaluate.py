"""
evaluate.py

Milestone 5: Evaluation.

Runs the debugging agent against a benchmark set of known bugs and
reports a success rate — the "proof it works" metric for the report.

Unlike run_agent.py (interactive, single-bug), this script:
- Runs unattended across MULTIPLE bugs
- Auto-accepts a patch if the test passes (no interactive prompt) —
  this only applies to batch evaluation; single-run mode in
  run_agent.py still pauses for human approval by design.
- Records pass/fail + iteration count for each bug
- Prints a summary table + overall success rate at the end
"""

import sys
import time
from dataclasses import dataclass
from pathlib import Path

from hypothesize import generate_hypothesis
from patch import generate_patch, apply_patch, rollback_patch
from reproduce import reproduce_bug

MAX_ITERATIONS = 3


@dataclass
class BenchmarkCase:
    name: str
    repo_path: str
    source_file: str
    test_id: str


@dataclass
class EvalResult:
    case_name: str
    fixed: bool
    iterations_used: int
    time_seconds: float


def run_single_case_auto(case: BenchmarkCase) -> EvalResult:
    """
    Same reproduce -> hypothesize -> patch -> verify loop as
    run_agent.py, but auto-accepts a working patch instead of asking
    for interactive approval. Used only for batch evaluation.
    """
    start = time.time()
    failure_output = None

    for iteration in range(1, MAX_ITERATIONS + 1):
        result = reproduce_bug(case.repo_path, case.test_id)

        if not result.reproduced:
            elapsed = time.time() - start
            return EvalResult(case.name, True, iteration - 1, elapsed)

        failure_output = result.stdout + result.stderr

        hypothesis = generate_hypothesis(case.source_file, failure_output, case.test_id)
        new_code = generate_patch(case.source_file, hypothesis, failure_output)
        apply_patch(case.source_file, new_code)

        verify_result = reproduce_bug(case.repo_path, case.test_id)

        if not verify_result.reproduced:
            # Auto-accept: batch mode, no interactive prompt.
            elapsed = time.time() - start
            return EvalResult(case.name, True, iteration, elapsed)
        else:
            # Patch didn't work — roll back before the next attempt.
            rollback_patch(case.source_file)
            failure_output = verify_result.stdout + verify_result.stderr

    elapsed = time.time() - start
    return EvalResult(case.name, False, MAX_ITERATIONS, elapsed)


def run_benchmark(cases: list[BenchmarkCase]) -> list[EvalResult]:
    results = []
    for i, case in enumerate(cases, start=1):
        print(f"[{i}/{len(cases)}] Running: {case.name} ...")
        result = run_single_case_auto(case)
        status = "FIXED" if result.fixed else "FAILED"
        print(f"    -> {status} (iterations: {result.iterations_used}, "
              f"time: {result.time_seconds:.1f}s)")
        results.append(result)
    return results


def print_summary(results: list[EvalResult]) -> None:
    total = len(results)
    fixed = sum(1 for r in results if r.fixed)

    print("\n" + "=" * 50)
    print("EVALUATION SUMMARY")
    print("=" * 50)
    for r in results:
        status = "PASS" if r.fixed else "FAIL"
        print(f"  [{status}] {r.case_name} "
              f"(iterations: {r.iterations_used}, {r.time_seconds:.1f}s)")
    print("-" * 50)
    print(f"Success rate: {fixed}/{total} ({100 * fixed / total:.0f}%)")
    print("=" * 50)


if __name__ == "__main__":
    # Usage: python evaluate.py <benchmark_repo_path>
    if len(sys.argv) != 2:
        print("Usage: python evaluate.py <benchmark_repo_path>")
        sys.exit(1)

    repo = sys.argv[1]

    cases = [
        BenchmarkCase(
            "bug_1_average",
            repo,
            f"{repo}\\mathlib\\bug_average.py",
            "tests/test_mathlib.py::test_average",
        ),
        BenchmarkCase(
            "bug_2_is_even",
            repo,
            f"{repo}\\mathlib\\bug_is_even.py",
            "tests/test_mathlib.py::test_is_even",
        ),
        BenchmarkCase(
            "bug_3_factorial",
            repo,
            f"{repo}\\mathlib\\bug_factorial.py",
            "tests/test_mathlib.py::test_factorial",
        ),
        BenchmarkCase(
            "bug_4_find_max",
            repo,
            f"{repo}\\mathlib\\bug_find_max.py",
            "tests/test_mathlib.py::test_find_max",
        ),
        BenchmarkCase(
            "bug_5_count_vowels",
            repo,
            f"{repo}\\mathlib\\bug_count_vowels.py",
            "tests/test_mathlib.py::test_count_vowels",
        ),
    ]

    results = run_benchmark(cases)
    print_summary(results)
