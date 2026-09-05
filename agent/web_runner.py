"""
web_runner.py

Shared core loop for the web frontend.

Milestone F4 change: instead of auto-accepting a working patch, the
generator now PAUSES — it yields a "diff" event with the patch diff
and STOPS (the SSE connection closes here). The browser then shows
the diff with Accept/Reject buttons and calls a separate endpoint:
- Accept -> nothing more to do, patch stays as-is.
- Reject -> the Flask route rolls back the patch, then reopens a
  NEW stream starting from the next iteration (via start_iteration).

This two-request design is necessary because SSE only flows one
direction (server -> browser); getting the human's decision back to
the server requires a separate, ordinary HTTP request.
"""

import subprocess
from pathlib import Path

from hypothesize import generate_hypothesis
from patch import generate_patch, apply_patch, rollback_patch
from reproduce import reproduce_bug

MAX_ITERATIONS = 3


def show_diff(backup_path: Path, current_path: Path) -> str:
    """Same diff logic as run_agent.py's CLI version."""
    result = subprocess.run(
        ["git", "diff", "--no-index", str(backup_path), str(current_path)],
        capture_output=True,
        text=True,
    )
    return result.stdout


def run_agent_web(repo_path: str, source_file_path: str, test_id: str, start_iteration: int = 1):
    """
    Generator version of the agent loop, resumable from a given
    iteration (used when a previous patch was rejected).

    Yields event dicts:
        {"type": "status", "message": ...}
        {"type": "hypothesis", "function": ..., "root_cause": ...}
        {"type": "diff", "diff": ..., "iteration": N}   <- pauses here
        {"type": "result", "fixed": True/False, "iterations": N}
    """
    yield {"type": "status", "message": f"Starting agent (max {MAX_ITERATIONS} iterations)"}

    failure_output = None

    for iteration in range(start_iteration, MAX_ITERATIONS + 1):
        yield {"type": "status", "message": f"--- Iteration {iteration}/{MAX_ITERATIONS} ---"}

        yield {"type": "status", "message": "Reproducing..."}
        result = reproduce_bug(repo_path, test_id)

        if not result.reproduced:
            yield {"type": "status", "message": "Test passes. Bug is fixed."}
            yield {"type": "result", "fixed": True, "iterations": iteration - 1}
            return

        failure_output = result.stdout + result.stderr
        yield {"type": "status", "message": "Confirmed: test still failing."}

        yield {"type": "status", "message": "Generating hypothesis..."}
        hypothesis = generate_hypothesis(source_file_path, failure_output, test_id)
        yield {
            "type": "hypothesis",
            "function": hypothesis.likely_function,
            "root_cause": hypothesis.root_cause,
            "confidence": hypothesis.confidence,
        }

        yield {"type": "status", "message": "Generating patch..."}
        new_code = generate_patch(source_file_path, hypothesis, failure_output)
        backup_path = apply_patch(source_file_path, new_code)

        yield {"type": "status", "message": "Re-running test to check the patch..."}
        verify_result = reproduce_bug(repo_path, test_id)

        if not verify_result.reproduced:
            # GUARDRAIL (F4): don't auto-accept. Show the diff and
            # PAUSE — wait for a human decision via a separate
            # request before doing anything more.
            diff_text = show_diff(backup_path, Path(source_file_path))
            yield {"type": "diff", "diff": diff_text, "iteration": iteration}
            return
        else:
            yield {"type": "status", "message": "Patch did NOT fix the bug. Rolling back..."}
            rollback_patch(source_file_path)
            failure_output = verify_result.stdout + verify_result.stderr

    yield {"type": "status", "message": f"Reached max iterations ({MAX_ITERATIONS}) without a fix."}
    yield {"type": "result", "fixed": False, "iterations": MAX_ITERATIONS}
