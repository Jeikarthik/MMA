"""Asset and clarification request management."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from mma.db import Store, utc_now


@dataclass(frozen=True)
class AssetRequest:
    id: str
    task_id: str
    prompt: str
    status: str
    answer: str | None


def create_asset_request(store: Store, task_id: str, prompt: str) -> str:
    """Create a blocking asset request for a task."""

    request_id = str(uuid4())
    with store.connect() as conn:
        conn.execute(
            """
            INSERT INTO asset_requests (id, task_id, prompt, status, created_at)
            VALUES (?, ?, ?, 'open', ?)
            """,
            (request_id, task_id, prompt, utc_now()),
        )
    store.transition(task_id, "awaiting_assets", {"asset_request_id": request_id, "prompt": prompt})
    return request_id


def answer_asset_request(store: Store, request_id: str, answer: str) -> None:
    """Resolve a previously opened asset request."""

    with store.connect() as conn:
        row = conn.execute(
            "SELECT task_id FROM asset_requests WHERE id = ? AND status = 'open'",
            (request_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"open asset request not found: {request_id}")
        conn.execute(
            """
            UPDATE asset_requests
            SET status = 'resolved', answer = ?, resolved_at = ?
            WHERE id = ?
            """,
            (answer, utc_now(), request_id),
        )
    store.transition(row["task_id"], "pending", {"resolved_asset_request_id": request_id})
