"""Watchdog helpers for stale task detection and resource safety."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from mma.config import load_config
from mma.db import Store
from mma.resources import check_resources


@dataclass(frozen=True)
class WatchdogReport:
    stale_tasks: list[str]
    resource_hard_stop: bool
    messages: list[str]


def run_watchdog(repo_root: Path, *, stale_minutes: int = 30) -> WatchdogReport:
    config = load_config(repo_root)
    store = Store(config.db_path)
    store.init()
    cutoff = datetime.now().astimezone() - timedelta(minutes=stale_minutes)
    stale: list[str] = []
    for task in store.list_tasks():
        if task.status not in {"executing", "validating", "scouting"}:
            continue
        # SQLite stores ISO timestamps with timezone; fetch direct to avoid expanding Task.
        with store.connect() as conn:
            row = conn.execute("SELECT updated_at FROM tasks WHERE id = ?", (task.id,)).fetchone()
        if row is None:
            continue
        updated = datetime.fromisoformat(row["updated_at"])
        if updated < cutoff:
            stale.append(task.id)
            store.transition(task.id, "failed", {"watchdog": "stale task"})
    resources = check_resources(config.safety)
    return WatchdogReport(
        stale_tasks=stale,
        resource_hard_stop=resources.hard_stop,
        messages=resources.messages,
    )
