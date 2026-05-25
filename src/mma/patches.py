"""Patch extraction and application helpers."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


class PatchError(RuntimeError):
    """Raised when model output cannot be converted into a patch."""


def extract_unified_diff(text: str) -> str:
    """Extract a unified diff from plain text or fenced output."""

    fenced = re.search(r"```(?:diff|patch)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    candidate = fenced.group(1).strip() if fenced else text.strip()
    if "diff --git " not in candidate and not candidate.startswith("--- "):
        raise PatchError("model output did not contain a unified diff")
    return candidate + "\n"


def apply_patch(repo_root: Path, patch_text: str, *, check: bool = False) -> subprocess.CompletedProcess[str]:
    args = ["git", "apply"]
    if check:
        args.append("--check")
    result = subprocess.run(args, input=patch_text, cwd=repo_root, capture_output=True, text=True)
    if result.returncode != 0:
        raise PatchError(result.stderr.strip() or result.stdout.strip() or "git apply failed")
    return result
