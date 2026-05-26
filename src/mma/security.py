"""Security checks for generated changes."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\s*=\s*['\"][^'\"]{8,}['\"]"),
    re.compile(r"(?i)\b(AKIA[0-9A-Z]{16})\b"),
]


class SecurityError(RuntimeError):
    """Raised when a security check fails."""


def scan_text_for_secrets(text: str) -> list[str]:
    findings: list[str] = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(pattern.pattern)
    return findings


def scan_files_for_secrets(repo_root: Path, files: list[str]) -> None:
    findings: list[str] = []
    for rel in files:
        path = (repo_root / rel).resolve()
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        matches = scan_text_for_secrets(text)
        if matches:
            findings.append(f"{rel}: {len(matches)} possible secret pattern(s)")
    if findings:
        raise SecurityError("Secret scan failed: " + "; ".join(findings))


def run_staged_secret_scan(repo_root: Path) -> None:
    """Run detect-secrets if installed, otherwise use built-in staged text scan."""

    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SecurityError(result.stderr.strip() or "could not list staged files")
    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not files:
        return
    detect = subprocess.run(
        ["python", "-m", "detect_secrets", "scan", "--all-files"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if detect.returncode == 0:
        return
    if "No module named detect_secrets" not in detect.stderr:
        raise SecurityError(detect.stdout.strip() or detect.stderr.strip())
    scan_files_for_secrets(repo_root, files)
