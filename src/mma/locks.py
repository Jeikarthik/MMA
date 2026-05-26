"""File lock helpers for task execution."""

from __future__ import annotations

from mma.db import Store, utc_now


class LockError(RuntimeError):
    """Raised when a file lock cannot be acquired."""


def acquire_file_locks(store: Store, task_id: str, paths: list[str]) -> None:
    with store.connect() as conn:
        for path in paths:
            row = conn.execute(
                "SELECT locked_by_task FROM file_locks WHERE file_path = ?",
                (path,),
            ).fetchone()
            if row is not None and row["locked_by_task"] != task_id:
                raise LockError(f"{path} is locked by task {row['locked_by_task']}")
        for path in paths:
            conn.execute(
                """
                INSERT OR REPLACE INTO file_locks (file_path, project_id, locked_by_task, locked_at)
                VALUES (?, 'default', ?, ?)
                """,
                (path, task_id, utc_now()),
            )


def release_file_locks(store: Store, task_id: str) -> None:
    with store.connect() as conn:
        conn.execute("DELETE FROM file_locks WHERE locked_by_task = ?", (task_id,))
