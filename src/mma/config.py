"""Configuration defaults for MMA."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path


CRITICAL_KEYWORDS = frozenset(
    {
        "auth",
        "authentication",
        "authorization",
        "payment",
        "billing",
        "security",
        "secret",
        "credential",
        "deploy",
        "deployment",
        "migration",
        "delete",
        "production",
        "ci/cd",
        "architecture",
    }
)


@dataclass(frozen=True)
class SafetyCaps:
    gpu_temp_warning_c: int = 78
    gpu_temp_hard_stop_c: int = 83
    min_free_ram_warning_gb: float = 4.0
    min_free_ram_hard_stop_gb: float = 3.0
    memory_pressure_warning_pct: int = 85
    memory_pressure_hard_stop_pct: int = 90
    stalled_generation_seconds: int = 180


@dataclass(frozen=True)
class LocalModels:
    simple: str = "gemma4-uncensored"
    coding: str = "qwen2.5-coder:7b"
    planning: str = "hermes3:8b"
    vision: str = "qwen2.5-vl:7b"
    embeddings: str = "nomic-embed-text"


@dataclass(frozen=True)
class NvidiaModels:
    coding: str = "qwen2.5-coder-72b-instruct"
    planning: str = "meta/llama-3.1-70b-instruct"
    reasoning: str = "nvidia/nemotron-70b-instruct"
    vision: str = "qwen2.5-vl-72b-instruct"
    image: str = "black-forest-labs/flux.1-dev"


@dataclass(frozen=True)
class AppConfig:
    repo_root: Path
    state_dir: Path
    db_path: Path
    ollama_base_url: str = "http://localhost:11434"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_api_key: str | None = None
    claude_api_key: str | None = None
    telegram_allowed_chat_ids: frozenset[int] = frozenset()
    safety: SafetyCaps = field(default_factory=SafetyCaps)
    local_models: LocalModels = field(default_factory=LocalModels)
    nvidia_models: NvidiaModels = field(default_factory=NvidiaModels)


def load_config(repo_root: Path | None = None) -> AppConfig:
    """Load configuration from environment variables and repo defaults."""

    root = (repo_root or Path.cwd()).resolve()
    state_dir = root / ".mma"
    return AppConfig(
        repo_root=root,
        state_dir=state_dir,
        db_path=state_dir / "mma.sqlite3",
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        nvidia_base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        nvidia_api_key=os.getenv("NVIDIA_API_KEY"),
        claude_api_key=os.getenv("ANTHROPIC_API_KEY"),
        telegram_allowed_chat_ids=_parse_chat_ids(os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "")),
    )


def _parse_chat_ids(value: str) -> frozenset[int]:
    ids: set[int] = set()
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        ids.add(int(item))
    return frozenset(ids)
