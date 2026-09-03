"""
hypothesize.py

Milestone 2: Hypothesis generation.

Takes the failure output captured by reproduce.py (Milestone 1) plus
the relevant source file, and asks Gemini to propose a hypothesis:
- which file/function is likely at fault
- why (root cause reasoning)
- a suggested direction for the fix

Important: this step does NOT write any code. It only reasons about
the bug and returns a structured hypothesis. Milestone 3 (patching)
will consume this hypothesis to actually generate a fix.

Beginner note: we ask Gemini to return JSON specifically (not free
prose) because Milestone 3 needs to read `file_path` and
`likely_function` programmatically — parsing free text reliably is
much harder and more fragile than parsing JSON.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path

import google.generativeai as genai


@dataclass
class Hypothesis:
    file_path: str
    likely_function: str
    root_cause: str
    suggested_fix_direction: str
    confidence: str  # "low" | "medium" | "high"


def _configure_gemini() -> None:
    """
    Reads the API key from the environment (never hardcoded) and
    configures the Gemini client.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set in this terminal session. "
            "Set it with: $env:GEMINI_API_KEY = (Read-Host \"Enter key\")"
        )
    genai.configure(api_key=api_key)


def _build_prompt(source_code: str, failure_output: str, test_id: str) -> str:
    """
    Builds the instruction we send to Gemini. We explicitly demand
    JSON-only output with a fixed schema, so parsing downstream is
    reliable.
    """
    return f"""You are a debugging assistant. A test has failed. Your job
is ONLY to form a hypothesis about the root cause — do NOT write a fix.

Failing test: {test_id}

--- Test failure output ---
{failure_output}

--- Relevant source code ---
{source_code}

Respond with ONLY a JSON object (no markdown fences, no extra text) in
exactly this shape:

{{
  "file_path": "relative path to the file most likely containing the bug",
  "likely_function": "name of the function most likely at fault",
  "root_cause": "one or two sentences explaining WHY this is likely the bug",
  "suggested_fix_direction": "one or two sentences on what kind of change would likely fix it, WITHOUT writing actual code",
  "confidence": "low, medium, or high"
}}
"""


def generate_hypothesis(
    source_file_path: str, failure_output: str, test_id: str
) -> Hypothesis:
    """
    Main entry point for Milestone 2.

    Example:
        generate_hypothesis(
            "sandbox/sample-buggy-repo/calculator/__init__.py",
            failure_output_from_milestone_1,
            "tests/test_calculator.py::test_average",
        )
    """
    _configure_gemini()

    source_path = Path(source_file_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    source_code = source_path.read_text()
    prompt = _build_prompt(source_code, failure_output, test_id)

    model = genai.GenerativeModel("gemini-3.5-flash-lite")
    response = model.generate_content(prompt)

    raw_text = response.text.strip()
    # Gemini sometimes wraps JSON in ```json fences even when told not to —
    # strip those defensively so parsing doesn't break.
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    data = json.loads(raw_text)

    return Hypothesis(
        file_path=data["file_path"],
        likely_function=data["likely_function"],
        root_cause=data["root_cause"],
        suggested_fix_direction=data["suggested_fix_direction"],
        confidence=data["confidence"],
    )


if __name__ == "__main__":
    # Manual test run:
    #   python hypothesize.py <source_file> <failure_output_file> <test_id>
    import sys

    if len(sys.argv) != 4:
        print("Usage: python hypothesize.py <source_file> <failure_output_file> <test_id>")
        sys.exit(1)

    source_file_arg = sys.argv[1]
    failure_output_arg = Path(sys.argv[2]).read_text()
    test_id_arg = sys.argv[3]

    hypothesis = generate_hypothesis(source_file_arg, failure_output_arg, test_id_arg)

    print("----- HYPOTHESIS -----")
    print(f"File:        {hypothesis.file_path}")
    print(f"Function:    {hypothesis.likely_function}")
    print(f"Root cause:  {hypothesis.root_cause}")
    print(f"Fix direction: {hypothesis.suggested_fix_direction}")
    print(f"Confidence:  {hypothesis.confidence}")
