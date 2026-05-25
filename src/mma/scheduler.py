"""Small sequential scheduler for pending tasks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mma.config import load_config
from mma.db import Store
from mma.orchestrator import Orchestrator, RunResult


@dataclass(frozen=True)
class SchedulerResult:
    attempted: int
    results: list[RunResult]


def run_pending(repo_root: Path, *, limit: int = 1) -> SchedulerResult:
    """Run pending tasks sequentially.

    This is intentionally conservative. DAG concurrency and file locks can build on this
    once the single-task loop is stable.
    """

    config = load_config(repo_root)
    store = Store(config.db_path)
    store.init()
    orchestrator = Orchestrator(config, store)
    results: list[RunResult] = []
    for task in store.list_tasks():
        if task.status != "pending":
            continue
        results.append(orchestrator.run_task(task.id))
        if len(results) >= limit:
            break
    return SchedulerResult(attempted=len(results), results=results)
