"""Context assembly for model calls."""

from __future__ import annotations

from dataclasses import dataclass

from mma.db import Store, Task
from mma.memory import search_memory


@dataclass(frozen=True)
class ContextPackage:
    prompt: str
    summaries_used: list[str]


def assemble_context(store: Store, task: Task, *, max_chars: int = 12000) -> ContextPackage:
    """Build a bounded prompt with task, prior failure digest, and repo memory."""

    summaries = search_memory(store, f"{task.title} {task.description}", limit=5)
    sections = [
        "Create a unified git diff for this task.",
        "",
        "Rules:",
        "- Return only a unified diff in a diff code block or raw diff.",
        "- Do not include explanations outside the diff.",
        "- Keep the change scoped to the task.",
        "- If required context or assets are missing, return exactly:",
        "  NEEDS_CONTEXT: <specific missing information>",
        "",
        f"Task type: {task.type}",
        f"Risk: {task.risk}",
        f"Validation profile: {task.validation_profile}",
        f"Title: {task.title}",
        "Description:",
        task.description,
    ]
    if task.failure_digest:
        sections.extend(["", "Previous failure digest:", task.failure_digest])
    elif task.error_log:
        sections.extend(["", "Previous failure:", task.error_log[:1000]])
    if summaries:
        sections.extend(["", "Relevant repo memory:"])
        sections.extend(f"- {entry.summary}" for entry in summaries)
    prompt = "\n".join(sections)
    if len(prompt) > max_chars:
        prompt = prompt[: max_chars - 100] + "\n[context truncated to budget]"
    return ContextPackage(prompt=prompt, summaries_used=[entry.path for entry in summaries])
