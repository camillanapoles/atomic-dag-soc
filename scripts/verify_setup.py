#!/usr/bin/env python3
"""
verify_setup.py: diagnostic checks for the development environment.

Run after `pip install -e ".[dev]"` to confirm everything is properly
plumbed. Prints a numbered checklist with pass/fail markers and a final
summary. Exits 0 on full success, 1 on any failure.

Usage:
    python scripts/verify_setup.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

CHECKS_PASSED: list[str] = []
CHECKS_FAILED: list[str] = []


def check(label: str, *, ok: bool, detail: str = "") -> None:
    """Record and print the result of a single check."""
    marker = "PASS" if ok else "FAIL"
    line = f"  [{marker}] {label}"
    if detail:
        line += f"  ({detail})"
    print(line)
    (CHECKS_PASSED if ok else CHECKS_FAILED).append(label)


def main() -> int:
    print("atomic-dag-soc setup verification\n")

    # 1. Python version
    py = sys.version_info
    check(
        "Python >= 3.11",
        ok=(py.major, py.minor) >= (3, 11),
        detail=f"found {py.major}.{py.minor}.{py.micro}",
    )

    # 2. Git available
    git_path = shutil.which("git")
    check("git is on PATH", ok=git_path is not None, detail=str(git_path))

    # 3. Package importable
    try:
        import atomic_dag

        check("atomic_dag is importable", ok=True, detail=f"v{atomic_dag.__version__}")
    except ImportError as e:
        check("atomic_dag is importable", ok=False, detail=str(e))

    # 4. CLI command on PATH
    cli_path = shutil.which("atomic-dag")
    check("atomic-dag CLI on PATH", ok=cli_path is not None, detail=str(cli_path))

    # 5. Dev tooling installed
    for tool in ("ruff", "mypy", "pytest"):
        path = shutil.which(tool)
        check(f"{tool} on PATH", ok=path is not None, detail=str(path))

    # 6. Project layout sanity
    root = Path(__file__).resolve().parent.parent
    for required in ("pyproject.toml", "src/atomic_dag/__init__.py", "tests/"):
        path = root / required
        check(f"{required} exists", ok=path.exists())

    # 7. Smoke test: --version returns
    if cli_path:
        try:
            result = subprocess.run(
                [cli_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            check(
                "atomic-dag --version executes",
                ok=result.returncode == 0,
                detail=result.stdout.strip() or "no output",
            )
        except (subprocess.TimeoutExpired, OSError) as e:
            check("atomic-dag --version executes", ok=False, detail=str(e))

    # Summary
    total = len(CHECKS_PASSED) + len(CHECKS_FAILED)
    print(f"\n{len(CHECKS_PASSED)}/{total} checks passed")
    if CHECKS_FAILED:
        print(f"\nFailed checks:\n  - " + "\n  - ".join(CHECKS_FAILED))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
