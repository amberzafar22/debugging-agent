"""
patch.py

Milestone 3: Patch + Verify.

Takes the hypothesis from hypothesize.py, asks Gemini to write the
actual corrected code, applies it to the real file (backing up the
original first so we can always undo), then re-runs the original
failing test to check whether the fix actually worked.

Beginner note: we ask for the FULL corrected file content rather than
a diff/patch format. Diffs are more "proper" but parsing and applying
them correctly is a separate hard problem on its own — full-file
replacement is simpler and good enough to prove the loop works.
"""

import os
import shutil
import sys
from pathlib import Path

import google.generativeai as genai

# Reuse pieces from the earlier milestones instead of duplicating code.
from hypothesize import Hypothesis, _configure_gemini
from reproduce import reproduce_bug


def _build_patch_prompt(source_code: str, hypothesis: Hypothesis, failure_output: str) -> str:
    return f"""You are a code-fixing assistant. Below is a hypothesis about
a bug, the original failing test output, and the full source code of
the file believed to contain the bug.

Your job: return the FULL corrected version of this file. Fix ONLY
what's needed to address the described root cause — do not refactor,
rename things, or change unrelated code.

--- Hypothesis ---
Likely function: {hypothesis.likely_function}
Root cause: {hypothesis.root_cause}
Suggested fix direction: {hypothesis.suggested_fix_direction}

--- Original failure output ---
{failure_output}

--- Original file content ---
{source_code}

Respond with ONLY the corrected file's full content. No explanations,
no markdown code fences, no extra text — just the raw corrected source
code, ready to be written directly to the file.
"""


def generate_patch(source_file_path: str, hypothesis: Hypothesis, failure_output: str) -> str:
    """
    Calls Gemini to produce the full corrected file content.
    Returns the new code as a string (does NOT write it to disk yet).
    """
    _configure_gemini()

    source_path = Path(source_file_path)
    original_code = source_path.read_text()

    prompt = _build_patch_prompt(original_code, hypothesis, failure_output)

    model = genai.GenerativeModel("gemini-3.5-flash-lite")
    response = model.generate_content(prompt)

    new_code = response.text.strip()
    # Defensive cleanup in case Gemini wraps it in a code fence anyway.
    if new_code.startswith("```"):
        lines = new_code.split("\n")
        lines = lines[1:]  # drop opening ```python or ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        new_code = "\n".join(lines)

    return new_code


def apply_patch(source_file_path: str, new_code: str) -> Path:
    """
    Backs up the original file (as .bak) and writes the new code in
    its place. Returns the backup path in case we need to roll back.
    """
    source_path = Path(source_file_path)
    backup_path = source_path.with_suffix(source_path.suffix + ".bak")

    # Only keep the FIRST backup (the true original) — don't overwrite
    # it if we patch more than once during a debugging session.
    if not backup_path.exists():
        shutil.copy2(source_path, backup_path)

    source_path.write_text(new_code)
    return backup_path


def rollback_patch(source_file_path: str) -> None:
    """Restores the original file from its .bak backup."""
    source_path = Path(source_file_path)
    backup_path = source_path.with_suffix(source_path.suffix + ".bak")
    if backup_path.exists():
        shutil.copy2(backup_path, source_path)
    else:
        raise FileNotFoundError(f"No backup found at {backup_path}")


if __name__ == "__main__":
    # Manual end-to-end run:
    #   python patch.py <repo_path> <source_file_path> <test_id>
    #
    # This ties Milestones 1-3 together in one script:
    #   1. Reproduce the bug (Milestone 1)
    #   2. Generate a hypothesis (Milestone 2)
    #   3. Generate + apply a patch, then re-verify (Milestone 3)
    from hypothesize import generate_hypothesis

    if len(sys.argv) != 4:
        print("Usage: python patch.py <repo_path> <source_file_path> <test_id>")
        sys.exit(1)

    repo_path_arg, source_file_arg, test_id_arg = sys.argv[1], sys.argv[2], sys.argv[3]

    print("Step 1: Reproducing the bug...")
    initial_result = reproduce_bug(repo_path_arg, test_id_arg)
    if not initial_result.reproduced:
        print("Test did not fail — nothing to fix. Exiting.")
        sys.exit(0)
    print("Confirmed: test fails.\n")

    print("Step 2: Generating hypothesis...")
    hypothesis = generate_hypothesis(
        source_file_arg, initial_result.stdout + initial_result.stderr, test_id_arg
    )
    print(f"Hypothesis: {hypothesis.likely_function} — {hypothesis.root_cause}\n")

    print("Step 3: Generating patch...")
    new_code = generate_patch(
        source_file_arg, hypothesis, initial_result.stdout + initial_result.stderr
    )
    backup_path = apply_patch(source_file_arg, new_code)
    print(f"Patch applied. Original backed up at: {backup_path}\n")

    print("Step 4: Re-running the test to verify the fix...")
    verify_result = reproduce_bug(repo_path_arg, test_id_arg)

    if not verify_result.reproduced:
        print("SUCCESS: Test now passes. Bug fixed.")
    else:
        print("Test still failing after patch:")
        print(verify_result.stdout)
        print(verify_result.stderr)
        print(f"\nTo undo this patch, run: rollback_patch('{source_file_arg}')")
