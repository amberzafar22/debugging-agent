"""
reproduce.py

Given a target repo and a failing test, this module:
1. Creates an isolated virtual environment for that repo (separate from
   the agent's own venv).
2. Installs the repo's dependencies.
3. Runs the specified test.
4. Reports whether it failed, and captures the output (stack trace etc.)
   so later stages (hypothesis generation) can read it.

Beginner note: we shell out to real `python -m venv` and `pytest`
subprocesses rather than importing the target repo's code directly.
This keeps the target repo's code fully isolated from our agent process,
which matters because buggy code could otherwise crash *us*.
"""

import subprocess
import sys
import venv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ReproductionResult:
    """Holds the outcome of one repro attempt."""
    reproduced: bool       # True if the test failed as expected
    stdout: str
    stderr: str
    return_code: int


def create_sandbox_env(repo_path: Path) -> Path:
    """
    Create a fresh virtual environment inside the target repo folder.
    Returns the path to that venv's python executable.
    """
    venv_dir = repo_path / ".agent_venv"
    if not venv_dir.exists():
        venv.EnvBuilder(with_pip=True).create(venv_dir)

    # On Windows, the venv's python.exe lives in Scripts/, not bin/
    python_exe = venv_dir / "Scripts" / "python.exe"
    return python_exe


def install_dependencies(repo_path: Path, python_exe: Path) -> None:
    """
    Install the target repo's dependencies into its sandbox venv.
    Assumes a requirements.txt for now — we can extend this later
    (pyproject.toml, setup.py) once the basic loop works.
    """
    # Install the repo's own package in editable mode, if it looks
    # like an installable Python package. This is what makes
    # `import black` (or whatever the repo's package is) work inside
    # its own tests — requirements.txt alone does NOT do this.
    if (repo_path / "pyproject.toml").exists() or (repo_path / "setup.py").exists():
        result = subprocess.run(
            [str(python_exe), "-m", "pip", "install", "-e", "."],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("WARNING: editable install of the package itself failed:")
            print(result.stderr)

    req_file = repo_path / "requirements.txt"
    if req_file.exists():
        result = subprocess.run(
            [str(python_exe), "-m", "pip", "install", "-r", str(req_file)],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("WARNING: requirements.txt install failed:")
            print(result.stderr)

    # Always make sure pytest itself is available in the sandbox
    result = subprocess.run(
        [str(python_exe), "-m", "pip", "install", "pytest"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to install pytest into sandbox venv:\n{result.stderr}"
        )


def run_test(repo_path: Path, python_exe: Path, test_id: str) -> ReproductionResult:
    """
    Run a single test (e.g. 'tests/test_math.py::test_add') and capture
    the result.

    A non-zero return code from pytest means the test failed —
    that's what "reproduced" means here.
    """
    result = subprocess.run(
        [str(python_exe), "-m", "pytest", test_id, "-v"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )

    return ReproductionResult(
        reproduced=(result.returncode != 0),
        stdout=result.stdout,
        stderr=result.stderr,
        return_code=result.returncode,
    )


def reproduce_bug(repo_path: str, test_id: str) -> ReproductionResult:
    """
    Main entry point for Milestone 1.

    Example:
        reproduce_bug("sandbox/some-repo", "tests/test_math.py::test_add")
    """
    repo = Path(repo_path).resolve()
    if not repo.exists():
        raise FileNotFoundError(f"Repo path does not exist: {repo}")

    python_exe = create_sandbox_env(repo)
    install_dependencies(repo, python_exe)
    result = run_test(repo, python_exe, test_id)
    return result


if __name__ == "__main__":
    # Simple manual test run from the command line:
    #   python reproduce.py <repo_path> <test_id>
    if len(sys.argv) != 3:
        print("Usage: python reproduce.py <repo_path> <test_id>")
        sys.exit(1)

    repo_path_arg, test_id_arg = sys.argv[1], sys.argv[2]
    outcome = reproduce_bug(repo_path_arg, test_id_arg)

    print(f"Reproduced failure: {outcome.reproduced}")
    print(f"Return code: {outcome.return_code}")
    print("----- STDOUT -----")
    print(outcome.stdout)
    print("----- STDERR -----")
    print(outcome.stderr)
