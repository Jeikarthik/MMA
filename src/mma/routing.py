"""Quality-first model routing."""

from __future__ import annotations

from dataclasses import dataclass

from mma.config import AppConfig, CRITICAL_KEYWORDS
from mma.db import Task


@dataclass(frozen=True)
class Route:
    provider: str
    model: str
    reason: str


def is_critical(task: Task) -> bool:
    text = f"{task.title} {task.description} {task.type}".lower()
    return task.risk == "high" or any(keyword in text for keyword in CRITICAL_KEYWORDS)


def choose_route(task: Task, config: AppConfig, *, local_safe: bool, override: str | None = None) -> Route:
    """Select a model route without letting local-first weaken critical tasks."""

    if override:
        if override.startswith("nvidia:"):
            return Route("nvidia", override.split(":", 1)[1], "manual NVIDIA override")
        if override.startswith("local:"):
            return Route("local", override.split(":", 1)[1], "manual local override")
        raise ValueError("override must start with 'local:' or 'nvidia:'")

    if is_critical(task):
        return Route("nvidia", config.nvidia_models.reasoning, "critical task routes directly to NVIDIA")

    if not local_safe:
        return Route("nvidia", config.nvidia_models.coding, "local resource health unsafe")

    if task.retry_count >= 2:
        return Route("nvidia", config.nvidia_models.coding, "local failed twice")

    if task.type in {"doc", "config", "summarize"}:
        return Route("local", config.local_models.simple, "ordinary simple task uses Gemma 4 local")

    if task.type == "vision":
        return Route("local", config.local_models.vision, "ordinary vision task uses local vision")

    return Route("local", config.local_models.coding, "ordinary task uses local coder")
