"""Git operations with narrow staging."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from mma.security import run_staged_secret_scan


class GitError(RuntimeError):
    """Raised for git workflow failures."""


def ensure_branch(repo_root: Path, branch: str) -> None:
    result = subprocess.run(
        ["git", "checkout", "-B", branch],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or result.stdout.strip())


def changed_files_from_patch(patch_text: str) -> list[str]:
    files: list[str] = []
    for match in re.finditer(r"^\+\+\+ b/(.+)$", patch_text, flags=re.MULTILINE):
        path = match.group(1).strip()
        if path != "/dev/null" and path not in files:
            files.append(path)
    return files


def commit_files(repo_root: Path, files: list[str], message: str) -> str:
    if not files:
        raise GitError("no files to commit")
    add = subprocess.run(["git", "add", "--", *files], cwd=repo_root, capture_output=True, text=True)
    if add.returncode != 0:
        raise GitError(add.stderr.strip() or add.stdout.strip())
    try:
        run_staged_secret_scan(repo_root)
    except RuntimeError as exc:
        raise GitError(str(exc)) from exc
    commit = subprocess.run(["git", "commit", "-m", message], cwd=repo_root, capture_output=True, text=True)
    if commit.returncode != 0:
        raise GitError(commit.stderr.strip() or commit.stdout.strip())
    rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True)
    if rev.returncode != 0:
        raise GitError(rev.stderr.strip() or rev.stdout.strip())
    return rev.stdout.strip()


def get_diff(repo_root: Path, ref: str = "HEAD") -> str:
    result = subprocess.run(["git", "diff", f"{ref}~1", ref], cwd=repo_root, capture_output=True, text=True)
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or result.stdout.strip())
    return result.stdout


def revert_commit(repo_root: Path, commit_sha: str) -> None:
    result = subprocess.run(
        ["git", "revert", "--no-edit", commit_sha],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or result.stdout.strip())
