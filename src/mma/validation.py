"""Stack-aware validation profiles."""

from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
from pathlib import Path


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    output: str


def run_validation(repo_root: Path, profile: str) -> ValidationResult:
    if profile == "python":
        commands = [["python", "-m", "compileall", "-q", "."]]
        commands.extend(_optional_python_checks())
        commands.append(["python", "-m", "pytest"])
        return _run_commands(repo_root, commands)
    if profile == "frontend":
        commands: list[list[str]] = []
        if (repo_root / "package.json").exists():
            commands.append(["npm", "test"])
            commands.append(["npm", "run", "build"])
        return _run_commands(repo_root, commands or [["git", "diff", "--check"]])
    if profile == "docs":
        return _run_commands(repo_root, [["git", "diff", "--check"]])
    if profile == "mixed":
        first = run_validation(repo_root, "python")
        second = run_validation(repo_root, "frontend")
        return ValidationResult(
            passed=first.passed and second.passed,
            output=f"{first.output}\n{second.output}".strip(),
        )
    return _run_commands(repo_root, [["git", "diff", "--check"]])


def _run_commands(repo_root: Path, commands: list[list[str]]) -> ValidationResult:
    output: list[str] = []
    for command in commands:
        if not _command_available(command[0]):
            output.append(f"SKIP {' '.join(command)}: command not available")
            continue
        result = subprocess.run(command, cwd=repo_root, capture_output=True, text=True)
        output.append(f"$ {' '.join(command)}")
        if result.stdout:
            output.append(result.stdout.strip())
        if result.stderr:
            output.append(result.stderr.strip())
        if result.returncode != 0:
            return ValidationResult(False, "\n".join(output))
    return ValidationResult(True, "\n".join(output))


def _command_available(command: str) -> bool:
    if command in {"python", "git"}:
        return True
    return shutil.which(command) is not None


def _optional_python_checks() -> list[list[str]]:
    checks: list[list[str]] = []
    if _module_available("ruff"):
        checks.append(["python", "-m", "ruff", "check", "."])
    if _module_available("mypy"):
        checks.append(["python", "-m", "mypy", "src"])
    if _module_available("bandit"):
        checks.append(["python", "-m", "bandit", "-q", "-r", "src"])
    return checks


def _module_available(module: str) -> bool:
    result = subprocess.run(
        ["python", "-c", f"import {module}"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
