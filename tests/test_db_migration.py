import sqlite3

from mma.db import Store


def test_migrates_missing_failure_digest(tmp_path):
    db_path = tmp_path / "mma.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE tasks (
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
                result_summary TEXT,
                error_log TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

    Store(db_path).init()

    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    assert "failure_digest" in columns
