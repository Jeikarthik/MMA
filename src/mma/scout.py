"""Deterministic pre-model scouting helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from mma.config import CRITICAL_KEYWORDS


ASSET_PATTERNS = {
    "api_key": re.compile(r"\b(api key|token|secret|webhook secret)\b", re.IGNORECASE),
    "credential": re.compile(r"\b(password|credential|database url|postgres_url)\b", re.IGNORECASE),
    "design": re.compile(r"\b(logo|brand color|font|mockup|wireframe|screenshot)\b", re.IGNORECASE),
    "deployment": re.compile(r"\b(netlify|vercel|aws|s3|docker hub|pypi|deploy)\b", re.IGNORECASE),
}


@dataclass(frozen=True)
class ScoutResult:
    risk: str
    validation_profile: str
    missing_assets: list[str]


def scout_task(repo_root: Path, description: str, task_type: str) -> ScoutResult:
    """Classify risk, validation profile, and likely missing assets."""

    text = f"{task_type} {description}".lower()
    risk = "high" if any(keyword in text for keyword in CRITICAL_KEYWORDS) else "normal"
    validation_profile = detect_validation_profile(repo_root, description, task_type)
    missing_assets = [
        asset_type for asset_type, pattern in ASSET_PATTERNS.items() if pattern.search(description)
    ]
    return ScoutResult(risk=risk, validation_profile=validation_profile, missing_assets=missing_assets)


def detect_validation_profile(repo_root: Path, description: str, task_type: str) -> str:
    """Pick the simplest validation profile that matches repo and task signals."""

    text = f"{task_type} {description}".lower()
    has_python = (repo_root / "pyproject.toml").exists() or any(repo_root.glob("*.py"))
    has_frontend = (repo_root / "package.json").exists()
    if task_type in {"doc", "diagram"} or any(word in text for word in {"readme", "docs", "diagram"}):
        return "docs"
    if has_python and has_frontend:
        return "mixed"
    if has_frontend or any(word in text for word in {"ui", "frontend", "react", "canvas", "browser"}):
        return "frontend"
    if has_python:
        return "python"
    return "generic"
