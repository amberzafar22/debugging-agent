"""
app.py

Milestone F5: Bug picker + polish.

Adds a registry of all 8 benchmark bugs (5 self-authored + 3 real
historical ones) so the dropdown in the browser can pick any of them,
instead of always running the same hardcoded apnumber bug.
"""

import json
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request, Response

AGENT_DIR = Path(__file__).resolve().parent.parent / "agent"
sys.path.insert(0, str(AGENT_DIR))

from web_runner import run_agent_web  # noqa: E402
from patch import rollback_patch  # noqa: E402

app = Flask(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def p(*parts):
    """Small helper: build an absolute path string from PROJECT_ROOT."""
    return str(PROJECT_ROOT.joinpath(*parts))


# Registry of all 8 benchmark bugs. Each entry has everything
# run_agent_web() needs: repo_path, source_file, test_id.
BUGS = {
    "real_apnumber": {
        "label": "[Real] apnumber — AP style zero handling",
        "repo": p("sandbox", "real-bugs-benchmark", "bug1-apnumber"),
        "source_file": p("sandbox", "real-bugs-benchmark", "bug1-apnumber", "humanize_mini", "bug_apnumber.py"),
        "test_id": "tests/test_apnumber.py::test_apnumber_zero",
    },
    "real_intword": {
        "label": "[Real] intword — rounding rollover edge case",
        "repo": p("sandbox", "real-bugs-benchmark", "bug2-intword"),
        "source_file": p("sandbox", "real-bugs-benchmark", "bug2-intword", "humanize_mini2", "bug_intword.py"),
        "test_id": "tests/test_intword.py::test_intword_rounds_up_to_next_unit",
    },
    "real_naturalsize": {
        "label": "[Real] naturalsize — negative byte counts",
        "repo": p("sandbox", "real-bugs-benchmark", "bug3-naturalsize"),
        "source_file": p("sandbox", "real-bugs-benchmark", "bug3-naturalsize", "humanize_mini3", "bug_naturalsize.py"),
        "test_id": "tests/test_naturalsize.py::test_naturalsize_negative_case",
    },
    "average": {
        "label": "average — wrong divisor",
        "repo": p("sandbox", "benchmark-repo"),
        "source_file": p("sandbox", "benchmark-repo", "mathlib", "bug_average.py"),
        "test_id": "tests/test_mathlib.py::test_average",
    },
    "is_even": {
        "label": "is_even — inverted condition",
        "repo": p("sandbox", "benchmark-repo"),
        "source_file": p("sandbox", "benchmark-repo", "mathlib", "bug_is_even.py"),
        "test_id": "tests/test_mathlib.py::test_is_even",
    },
    "factorial": {
        "label": "factorial — off-by-one range",
        "repo": p("sandbox", "benchmark-repo"),
        "source_file": p("sandbox", "benchmark-repo", "mathlib", "bug_factorial.py"),
        "test_id": "tests/test_mathlib.py::test_factorial",
    },
    "find_max": {
        "label": "find_max — skips first element",
        "repo": p("sandbox", "benchmark-repo"),
        "source_file": p("sandbox", "benchmark-repo", "mathlib", "bug_find_max.py"),
        "test_id": "tests/test_mathlib.py::test_find_max",
    },
    "count_vowels": {
        "label": "count_vowels — misses uppercase vowels",
        "repo": p("sandbox", "benchmark-repo"),
        "source_file": p("sandbox", "benchmark-repo", "mathlib", "bug_count_vowels.py"),
        "test_id": "tests/test_mathlib.py::test_count_vowels",
    },
}


@app.route("/")
def index():
    # Pass the bug list to the template so the dropdown can be built
    # server-side — id + label only, not the internal paths.
    bug_options = [{"id": key, "label": val["label"]} for key, val in BUGS.items()]
    return render_template("index.html", bugs=bug_options)


@app.route("/run-stream")
def run_stream():
    bug_id = request.args.get("bug_id", default="real_apnumber")
    start_iteration = request.args.get("start_iteration", default=1, type=int)

    bug = BUGS[bug_id]

    def event_stream():
        for step in run_agent_web(bug["repo"], bug["source_file"], bug["test_id"], start_iteration):
            yield f"data: {json.dumps(step)}\n\n"

    return Response(event_stream(), mimetype="text/event-stream")


@app.route("/approve", methods=["POST"])
def approve():
    return jsonify({"status": "accepted"})


@app.route("/reject", methods=["POST"])
def reject():
    data = request.get_json()
    bug_id = data.get("bug_id", "real_apnumber")
    current_iteration = data.get("iteration", 1)

    bug = BUGS[bug_id]
    rollback_patch(bug["source_file"])

    return jsonify({"status": "rejected", "next_iteration": current_iteration + 1})


if __name__ == "__main__":
    app.run(debug=True, port=5050, use_reloader=False)
