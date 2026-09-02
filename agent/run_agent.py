"""
run_agent.py

Milestone 4: Guardrails.

This is the full orchestrated loop, wrapping Milestones 1-3 with
safety mechanisms:

1. ITERATION CAP — if a patch doesn't fix the bug, we loop back to
   hypothesis generation with the new failure, but only up to
   MAX_ITERATIONS times. Prevents infinite loops / runaway API usage
   on a bug the agent just can't solve.

2. AUTO-ROLLBACK — if a patch is applied and the test still fails,
   we restore the original file BEFORE trying again. This stops
   failed attempts from stacking on top of each other, which would
   make the code increasingly broken and confuse the next hypothesis.

3. INTERACTIVE DIFF REVIEW — before a patch is treated as "accepted"
   (kept, not rolled back), we show the human the diff and require
   explicit y/n confirmation. This keeps a human in the loop rather
   than letting the agent silently ship changes.
"""

import subprocess
import sys
from pathlib import Path

from hypothesize import generate_hypothesis
from patch import generate_patch, apply_patch, rollback_patch
from reproduce import reproduce_bug

MAX_ITERATIONS = 3


def show_diff(backup_path: Path, current_path: Path) -> str:
    """
    Shows the diff between the backup (original) and the current
    (patched) file, using git's diff engine for readable output.
    Returns the diff text so it can also be logged if needed.
    """
    result = subprocess.run(
        ["git", "diff", "--no-index", str(backup_path), str(current_path)],
        capture_output=True,
        text=True,
    )
    # git diff --no-index returns exit code 1 when files differ —
    # that's expected, not an error, so we don't check returncode here.
    return result.stdout


def ask_human_to_approve(diff_text: str) -> bool:
    """
    Shows the diff and asks the human to explicitly approve it.
    This is the guardrail that keeps a human in the loop.
    """
    print("\n" + "=" * 60)
    print("PROPOSED PATCH — review before accepting:")
    print("=" * 60)
    print(diff_text)
    print("=" * 60)

    answer = input("Accept this patch? [y/n]: ").strip().lower()
    return answer == "y"


def run_agent(repo_path: str, source_file_path: str, test_id: str) -> None:
    print(f"Starting debugging agent (max {MAX_ITERATIONS} iterations)\n")

    failure_output = None

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n--- Iteration {iteration}/{MAX_ITERATIONS} ---")

        print("Reproducing...")
        result = reproduce_bug(repo_path, test_id)

        if not result.reproduced:
            print("Test passes. Bug is fixed — stopping.")
            return

        failure_output = result.stdout + result.stderr
        print("Confirmed: test still failing.")

        print("Generating hypothesis...")
        hypothesis = generate_hypothesis(source_file_path, failure_output, test_id)
        print(f"  Hypothesis: {hypothesis.likely_function} — {hypothesis.root_cause}")

        print("Generating patch...")
        new_code = generate_patch(source_file_path, hypothesis, failure_output)
        backup_path = apply_patch(source_file_path, new_code)

        print("Re-running test to check the patch...")
        verify_result = reproduce_bug(repo_path, test_id)

        source_path = Path(source_file_path)

        if not verify_result.reproduced:
            # Patch appears to work — show it to the human before
            # truly accepting it.
            diff_text = show_diff(backup_path, source_path)
            approved = ask_human_to_approve(diff_text)

            if approved:
                print("Patch approved by user. Bug fixed — stopping.")
                return
            else:
                print("Patch rejected by user. Rolling back and trying again...")
                rollback_patch(source_file_path)
                # Loop continues to next iteration for a fresh attempt.
        else:
            # GUARDRAIL: patch did not fix it — roll back before
            # trying again, so failed attempts don't stack.
            print("Patch did NOT fix the bug. Rolling back...")
            rollback_patch(source_file_path)
            failure_output = verify_result.stdout + verify_result.stderr

    print(f"\nReached max iterations ({MAX_ITERATIONS}) without a fix.")
    print("Last known failure:")
    print(failure_output)


if __name__ == "__main__":
    # Usage: python run_agent.py <repo_path> <source_file_path> <test_id>
    if len(sys.argv) != 4:
        print("Usage: python run_agent.py <repo_path> <source_file_path> <test_id>")
        sys.exit(1)

    run_agent(sys.argv[1], sys.argv[2], sys.argv[3])
