"""Browser/visual QA command hooks."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


class BrowserQaError(RuntimeError):
    """Raised when browser QA cannot run or fails."""


def run_browser_qa(repo_root: Path, target_url: str | None = None) -> str:
    """Run a configured browser QA command.

    Configure `MMA_BROWSER_QA_COMMAND` with a command that exits non-zero on failure.
    The target URL is exposed as `MMA_BROWSER_QA_URL`.
    """

    command = os.getenv("MMA_BROWSER_QA_COMMAND")
    if not command:
        raise BrowserQaError("MMA_BROWSER_QA_COMMAND is not configured")
    env = os.environ.copy()
    if target_url:
        env["MMA_BROWSER_QA_URL"] = target_url
    result = subprocess.run(command, cwd=repo_root, shell=True, capture_output=True, text=True, env=env)
    output = "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part)
    if result.returncode != 0:
        raise BrowserQaError(output or f"browser QA command failed with {result.returncode}")
    return output or "browser QA passed"
