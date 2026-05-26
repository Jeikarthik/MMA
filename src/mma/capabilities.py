"""Permission-gated skill and plugin capability registry."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from uuid import uuid4

from mma.browser_qa import run_browser_qa
from mma.db import Store, utc_now
from mma.memory import index_repo, search_memory


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


def invoke_capability(
    store: Store,
    repo_root: Path,
    *,
    name: str,
    arguments: dict,
    approved: bool = False,
) -> dict:
    capabilities = {capability.name: capability for capability in list_capabilities(store)}
    if name not in capabilities:
        raise ValueError(f"capability not found: {name}")
    capability = capabilities[name]
    if not capability.enabled:
        raise ValueError(f"capability is disabled: {name}")
    if capability.requires_approval and not approved:
        return {"status": "awaiting_approval", "capability": name}
    if name == "repo-inspect":
        query = arguments.get("query")
        if query:
            return {
                "status": "complete",
                "results": [
                    {"path": item.path, "summary": item.summary}
                    for item in search_memory(store, str(query), limit=int(arguments.get("limit", 5)))
                ],
            }
        return {"status": "complete", "indexed": len(index_repo(store, repo_root))}
    if name == "browser-qa":
        return {
            "status": "complete",
            "output": run_browser_qa(repo_root, arguments.get("target_url")),
        }
    raise ValueError(f"capability adapter not implemented: {name}")
