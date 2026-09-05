# Autonomous Debugging Agent

An agent that behaves like a junior developer fixing a bug: it reproduces a
failing test, forms a hypothesis about the root cause, writes a patch,
and re-tests — looping until the test passes or it runs out of attempts.
Evaluated on a small benchmark of known bugs with a measurable success rate.

## Why this design

Real debugging follows a discipline: reproduce reliably before you touch
anything, form a theory before you edit code, and verify after every change.
This project mirrors that discipline directly in its architecture, rather
than asking an LLM to "just fix the bug" in one shot.

## Architecture

```
Reproduce → Hypothesize → Patch → Verify
    ↑                                │
    └──────── loop (max 3x) ─────────┘
```

| Stage | File | What it does |
|---|---|---|
| 1. Reproduce | `agent/reproduce.py` | Clones/reads a target repo, builds an isolated sandbox venv for it, installs its dependencies + the package itself, and runs one specific test. Captures pass/fail and full output. |
| 2. Hypothesize | `agent/hypothesize.py` | Sends the failure output + relevant source code to Gemini, asking for a structured (JSON) hypothesis: likely file, function, root cause, and fix direction — **without writing any code**. |
| 3. Patch | `agent/patch.py` | Sends the hypothesis + original code to Gemini, asking for the full corrected file. Backs up the original before writing the fix, so any patch can be undone. |
| 4. Guardrails | `agent/run_agent.py` | Wraps the loop with: an iteration cap (max 3 attempts), auto-rollback if a patch doesn't fix the bug, and an interactive diff-review step — the agent never silently accepts its own patch. |
| 5. Evaluation | `agent/evaluate.py` | Runs the full loop unattended (auto-accepting passing patches) across a benchmark set of known bugs and reports a success rate. |

## Design decisions worth knowing (and why)

- **Process-level isolation (subprocess + venv), not Docker.** Simpler to
  set up and reason about; keeps complexity budget on the agent logic
  rather than container infrastructure. Trade-off: less airtight isolation
  than containers would give.
- **Full-file patches, not diffs.** Gemini returns the entire corrected
  file rather than a unified diff. Simpler to apply reliably; the
  trade-off is it's a coarser edit than a true diff-based patch tool
  would produce.
- **JSON-only LLM responses.** Both the hypothesis and patch-generation
  prompts demand structured output specifically so later stages can parse
  results programmatically, instead of relying on fragile text parsing.
- **Interactive approval by default; auto-accept only for batch eval.**
  A human stays in the loop for real runs. Evaluation mode auto-accepts
  passing patches purely so a multi-bug benchmark can run unattended.

## Setup

```powershell
git clone https://github.com/amberzafar22/debugging-agent.git
cd debugging-agent
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install google-generativeai
```

Get a free Gemini API key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey),
then set it for your session:

```powershell
$env:GEMINI_API_KEY = (Read-Host "Enter key")
```

## Usage

**Single bug, interactive (asks for your approval before accepting a fix):**
```powershell
python agent\run_agent.py <repo_path> <source_file_path> <test_id>
```

**Full benchmark evaluation (unattended, 5 known bugs):**
```powershell
python agent\evaluate.py benchmarks\benchmark-repo
```

## Web frontend

A Flask-based web UI lets you watch the agent work live in the browser,
instead of reading terminal output.

```
frontend/
├── app.py                 # Flask routes
└── templates/index.html   # UI + JavaScript
agent/web_runner.py         # generator version of the loop, shared by the UI
```

**How it works:**
- The core loop is a Python **generator** (`web_runner.py`) that `yield`s
  one event per step (status, hypothesis, diff, result) instead of just
  printing.
- The browser connects via **Server-Sent Events (SSE)** — a one-way
  streaming connection — so each step appears the instant it happens,
  not all at once at the end.
- When a patch passes its test, the generator **pauses** and sends a
  `diff` event instead of auto-accepting. The browser shows the diff
  with Accept/Reject buttons. Since SSE only flows server→browser, the
  human's decision comes back via a separate `/approve` or `/reject`
  request — a rejection rolls back the patch and reopens a **new**
  stream starting from the next iteration, so the loop resumes exactly
  where it left off.
- A dropdown lets you pick any of the 8 benchmark bugs to run live.

**Run it:**
```powershell
cd frontend
python app.py
```
Then open `http://localhost:5050`.

## Evaluation results


Benchmark: 5 small Python functions, each with one deliberately planted
bug, ranging from simple off-by-one errors to a case-sensitivity edge case.

| Bug | Difficulty | Result | Iterations |
|---|---|---|---|
| `average` — wrong divisor | Easy | Fixed | 1 |
| `is_even` — inverted condition | Easy | Fixed | 1 |
| `factorial` — off-by-one range | Medium | Fixed | 1 |
| `find_max` — skips first element | Medium | Fixed | 1 |
| `count_vowels` — misses uppercase vowels | Harder | Fixed | 1 |

**Success rate: 5/5 (100%)**

Also tested against 3 real historical bugs from the [humanize](https://github.com/python-humanize/humanize)
library — each verified to reproduce exactly as it did in real history,
and resolved by the agent independently (in one case, producing a fix
character-for-character identical to the real historical commit).

| Real bug | Source commit | Result |
|---|---|---|
| `apnumber` — AP style zero handling | `2f179b6` | Fixed |
| `intword` — rounding rollover edge case | `818c9b3` | Fixed |
| `naturalsize` — negative byte counts | `db96782` | Fixed |

**Combined: 8/8 (100%)** across both tiers.

The guardrails were also stress-tested directly: a deliberately
unsatisfiable test was used to force the agent through all 3 iterations,
confirming the iteration cap stops it correctly, and that auto-rollback
fires after every failed attempt (verified via terminal output showing
"Rolling back..." three times, ending in "Reached max iterations (3)
without a fix").

## Known limitations

- Tested only on small, self-contained Python functions — not yet
  validated on larger, multi-file, or cross-language bugs.
- Reproduction currently treats any non-zero pytest exit code as "bug
  reproduced," which doesn't distinguish a real assertion failure from a
  test-collection or environment error. Parsing pytest's structured JSON
  output would make this more robust.
- The benchmark set is self-authored, not drawn from real-world GitHub
  issues — a natural next step would be evaluating against a small set
  of real, historical bug-fix commits.
- One benchmark case (`count_vowels`) initially had a test that didn't
  actually exercise its own planted bug — a reminder that an agent's
  ability to catch a bug is only as good as the test verifying it.

## Project structure

```
debugging-agent/
├── agent/
│   ├── reproduce.py     # Milestone 1
│   ├── hypothesize.py   # Milestone 2
│   ├── patch.py         # Milestone 3
│   ├── run_agent.py     # Milestone 4 (guarded, interactive CLI loop)
│   ├── evaluate.py       # Milestone 5 (batch evaluation)
│   ├── evaluate_real_bugs.py  # evaluation for the real-bugs tier
│   └── web_runner.py     # generator loop shared by the web frontend
├── frontend/
│   ├── app.py             # Flask routes
│   └── templates/index.html
├── benchmarks/
│   └── benchmark-repo/    # 5 self-authored known bugs
└── sandbox/                 # gitignored — temporary target repo clones,
                              # also holds real-bugs-benchmark/ at runtime
```
