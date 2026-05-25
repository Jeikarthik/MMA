"""Simple DAG creation and validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mma.db import Store


@dataclass(frozen=True)
class DagTask:
    key: str
    title: str
    description: str
    task_type: str = "code"
    risk: str = "auto"
    validation_profile: str = "auto"
    depends_on: tuple[str, ...] = ()


def create_dag(store: Store, tasks: list[DagTask]) -> dict[str, str]:
    """Create tasks and dependencies from a validated DAG spec."""

    validate_dag(tasks)
    key_to_id: dict[str, str] = {}
    for item in tasks:
        task = store.create_task(
            title=item.title,
            description=item.description,
            task_type=item.task_type,
            risk="normal" if item.risk == "auto" else item.risk,
            validation_profile="generic" if item.validation_profile == "auto" else item.validation_profile,
        )
        key_to_id[item.key] = task.id
    for item in tasks:
        for dep in item.depends_on:
            store.add_dependency(key_to_id[item.key], key_to_id[dep])
    return key_to_id


def validate_dag(tasks: list[DagTask]) -> None:
    keys = [task.key for task in tasks]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate DAG task key")
    known = set(keys)
    for task in tasks:
        missing = set(task.depends_on) - known
        if missing:
            raise ValueError(f"task {task.key} depends on unknown task(s): {sorted(missing)}")
    visiting: set[str] = set()
    visited: set[str] = set()
    by_key = {task.key: task for task in tasks}

    def visit(key: str) -> None:
        if key in visited:
            return
        if key in visiting:
            raise ValueError("DAG contains a cycle")
        visiting.add(key)
        for dep in by_key[key].depends_on:
            visit(dep)
        visiting.remove(key)
        visited.add(key)

    for key in keys:
        visit(key)


def dag_tasks_from_json(payload: list[dict[str, Any]]) -> list[DagTask]:
    return [
        DagTask(
            key=str(item["key"]),
            title=item["title"],
            description=item["description"],
            task_type=item.get("type", "code"),
            risk=item.get("risk", "auto"),
            validation_profile=item.get("validation_profile", "auto"),
            depends_on=tuple(item.get("depends_on", ())),
        )
        for item in payload
    ]
