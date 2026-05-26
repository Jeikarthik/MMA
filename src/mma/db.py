"""SQLite persistence for MMA."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4


SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    risk TEXT NOT NULL DEFAULT 'normal',
    validation_profile TEXT NOT NULL DEFAULT 'python',
    model_provider TEXT,
    model_name TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    branch TEXT,
    commit_sha TEXT,
    files_modified TEXT NOT NULL DEFAULT '[]',
    failure_digest TEXT,
    result_summary TEXT,
    error_log TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_deps (
    task_id TEXT NOT NULL,
    depends_on TEXT NOT NULL,
    PRIMARY KEY (task_id, depends_on),
    FOREIGN KEY(task_id) REFERENCES tasks(id),
    FOREIGN KEY(depends_on) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS asset_requests (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    prompt TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    answer TEXT,
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS capabilities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    adapter_type TEXT NOT NULL,
    permissions TEXT NOT NULL DEFAULT '[]',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS provider_usage (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_cost REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS repo_memory (
    path TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL,
    summary TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS file_locks (
    file_path TEXT NOT NULL,
    project_id TEXT NOT NULL DEFAULT 'default',
    locked_by_task TEXT NOT NULL,
    locked_at TEXT NOT NULL,
    PRIMARY KEY (file_path, project_id),
    FOREIGN KEY(locked_by_task) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS credentials (
    key TEXT PRIMARY KEY,
    value_encrypted TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    description: str
    type: str
    status: str
    risk: str
    validation_profile: str
    model_provider: str | None
    model_name: str | None
    retry_count: int
    branch: str | None
    files_modified: list[str]
    result_summary: str | None
    error_log: str | None
    commit_sha: str | None = None
    failure_digest: str | None = None


class Store:
    """Small SQLite wrapper with explicit state transitions."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            self._migrate(conn)

    def create_task(
        self,
        *,
        title: str,
        description: str,
        task_type: str,
        risk: str,
        validation_profile: str,
    ) -> Task:
        task_id = str(uuid4())
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO tasks (
                    id, title, description, type, status, risk, validation_profile,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?)
                """,
                (task_id, title, description, task_type, risk, validation_profile, now, now),
            )
            self._insert_event(conn, task_id, "task_created", {"title": title})
        task = self.get_task(task_id)
        assert task is not None
        return task

    def get_task(self, task_id: str) -> Task | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._row_to_task(row) if row else None

    def list_tasks(self) -> list[Task]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM tasks ORDER BY created_at").fetchall()
        return [self._row_to_task(row) for row in rows]

    def add_dependency(self, task_id: str, depends_on: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO task_deps (task_id, depends_on) VALUES (?, ?)",
                (task_id, depends_on),
            )
            self._insert_event(conn, task_id, "dependency_added", {"depends_on": depends_on})

    def ready_tasks(self) -> list[Task]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT t.*
                FROM tasks t
                WHERE t.status = 'pending'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM task_deps d
                    JOIN tasks dep ON dep.id = d.depends_on
                    WHERE d.task_id = t.id
                      AND dep.status != 'complete'
                  )
                ORDER BY t.created_at
                """
            ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def transition(self, task_id: str, status: str, payload: dict[str, Any] | None = None) -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, task_id),
            )
            self._insert_event(conn, task_id, "state_transition", {"status": status, **(payload or {})})

    def update_task(self, task_id: str, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = utc_now()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = [json.dumps(value) if isinstance(value, (list, dict)) else value for value in fields.values()]
        values.append(task_id)
        with self.connect() as conn:
            conn.execute(f"UPDATE tasks SET {assignments} WHERE id = ?", values)

    def log_usage(
        self,
        *,
        provider: str,
        model: str,
        status: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        estimated_cost: float = 0,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO provider_usage (
                    id, provider, model, input_tokens, output_tokens, estimated_cost, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    provider,
                    model,
                    input_tokens,
                    output_tokens,
                    estimated_cost,
                    status,
                    utc_now(),
                ),
            )

    @staticmethod
    def _insert_event(
        conn: sqlite3.Connection, task_id: str | None, event_type: str, payload: dict[str, Any]
    ) -> None:
        conn.execute(
            "INSERT INTO events (id, task_id, event_type, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid4()), task_id, event_type, json.dumps(payload), utc_now()),
        )

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(tasks)").fetchall()
        }
        if "failure_digest" not in columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN failure_digest TEXT")
        lock_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(file_locks)").fetchall()
        }
        if lock_columns and "locked_by_task" not in lock_columns:
            conn.execute("DROP TABLE file_locks")
            conn.execute(
                """
                CREATE TABLE file_locks (
                    file_path TEXT NOT NULL,
                    project_id TEXT NOT NULL DEFAULT 'default',
                    locked_by_task TEXT NOT NULL,
                    locked_at TEXT NOT NULL,
                    PRIMARY KEY (file_path, project_id),
                    FOREIGN KEY(locked_by_task) REFERENCES tasks(id)
                )
                """
            )

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            type=row["type"],
            status=row["status"],
            risk=row["risk"],
            validation_profile=row["validation_profile"],
            model_provider=row["model_provider"],
            model_name=row["model_name"],
            retry_count=row["retry_count"],
            branch=row["branch"],
            commit_sha=row["commit_sha"],
            files_modified=json.loads(row["files_modified"]),
            result_summary=row["result_summary"],
            error_log=row["error_log"],
            failure_digest=row["failure_digest"],
        )
