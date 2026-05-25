"""Permission-gated skill and plugin capability registry."""

from __future__ import annotations

from dataclasses import dataclass
import json
from uuid import uuid4

from mma.db import Store, utc_now


MUTATING_PERMISSIONS = frozenset({"write", "network", "secret", "install", "external_tool"})


@dataclass(frozen=True)
class Capability:
    id: str
    name: str
    adapter_type: str
    permissions: set[str]
    enabled: bool

    @property
    def requires_approval(self) -> bool:
        return bool(self.permissions & MUTATING_PERMISSIONS)


def register_capability(
    store: Store,
    *,
    name: str,
    adapter_type: str,
    permissions: set[str] | None = None,
) -> str:
    """Register or replace a capability definition."""

    capability_id = str(uuid4())
    with store.connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO capabilities
                (id, name, adapter_type, permissions, enabled, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (
                capability_id,
                name,
                adapter_type,
                json.dumps(sorted(permissions or set())),
                utc_now(),
            ),
        )
    return capability_id


def list_capabilities(store: Store) -> list[Capability]:
    """List registered capabilities."""

    with store.connect() as conn:
        rows = conn.execute("SELECT * FROM capabilities ORDER BY name").fetchall()
    return [
        Capability(
            id=row["id"],
            name=row["name"],
            adapter_type=row["adapter_type"],
            permissions=set(json.loads(row["permissions"])),
            enabled=bool(row["enabled"]),
        )
        for row in rows
    ]


def seed_default_capabilities(store: Store) -> None:
    """Seed the minimum safe v1 capability set."""

    register_capability(store, name="repo-inspect", adapter_type="native", permissions=set())
    register_capability(store, name="browser-qa", adapter_type="browser", permissions={"external_tool"})
    register_capability(store, name="github-pr", adapter_type="github", permissions={"network"})
