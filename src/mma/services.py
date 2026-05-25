"""Application service layer shared by CLI, MCP, and future APIs."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from mma.assets import answer_asset_request, create_asset_request
from mma.capabilities import list_capabilities, seed_default_capabilities
from mma.config import load_config
from mma.db import Store, Task
from mma.git_ops import get_diff, revert_commit
from mma.github_api import build_pr_body, create_pull_request
from mma.memory import index_repo, search_memory
from mma.orchestrator import Orchestrator
from mma.resources import check_resources
from mma.scout import scout_task


class MmaService:
    """High-level facade for MMA operations."""

    def __init__(self, repo_root: Path) -> None:
        self.config = load_config(repo_root)
        self.store = Store(self.config.db_path)
        self.store.init()

    def init(self) -> dict[str, Any]:
        seed_default_capabilities(self.store)
        return {"db_path": str(self.config.db_path), "status": "initialized"}

    def create_task(
        self,
        *,
        description: str,
        title: str | None = None,
        task_type: str = "code",
        risk: str = "normal",
        validation_profile: str = "python",
    ) -> dict[str, Any]:
        scout = scout_task(self.config.repo_root, description, task_type)
        if risk == "auto" or validation_profile == "auto":
            if risk == "auto":
                risk = scout.risk
            if validation_profile == "auto":
                validation_profile = scout.validation_profile
        task = self.store.create_task(
            title=title or description[:80],
            description=description,
            task_type=task_type,
            risk=risk,
            validation_profile=validation_profile,
        )
        if scout.missing_assets:
            create_asset_request(
                self.store,
                task.id,
                "Need operator-provided assets before execution: "
                + ", ".join(sorted(scout.missing_assets)),
            )
            task = self.store.get_task(task.id)
            assert task is not None
        return task_to_dict(task)

    def list_tasks(self) -> list[dict[str, Any]]:
        return [task_to_dict(task) for task in self.store.list_tasks()]

    def get_task(self, task_id: str) -> dict[str, Any]:
        task = self.store.get_task(task_id)
        if task is None:
            raise ValueError(f"task not found: {task_id}")
        return task_to_dict(task)

    def run_task(self, task_id: str, model: str | None = None) -> dict[str, Any]:
        result = Orchestrator(self.config, self.store).run_task(task_id, model_override=model)
        return asdict(result)

    def pause_task(self, task_id: str) -> dict[str, str]:
        self.store.transition(task_id, "paused")
        return {"status": "paused", "task_id": task_id}

    def retry_task(self, task_id: str) -> dict[str, str]:
        self.store.transition(task_id, "pending")
        return {"status": "pending", "task_id": task_id}

    def rollback_task(self, task_id: str) -> dict[str, str]:
        task = self.store.get_task(task_id)
        if task is None:
            raise ValueError(f"task not found: {task_id}")
        if not task.commit_sha:
            raise ValueError("task has no commit to roll back")
        revert_commit(self.config.repo_root, task.commit_sha)
        self.store.transition(task_id, "rolled_back")
        return {"status": "rolled_back", "task_id": task_id, "commit_sha": task.commit_sha}

    def get_diff(self, task_id: str) -> dict[str, str]:
        task = self.store.get_task(task_id)
        if task is None:
            raise ValueError(f"task not found: {task_id}")
        if not task.commit_sha:
            raise ValueError("task has no committed diff")
        return {"task_id": task_id, "diff": get_diff(self.config.repo_root, task.commit_sha)}

    def create_pr(
        self,
        *,
        repo_full_name: str,
        head: str,
        base: str = "main",
        title: str,
        summary: str,
        validation: str,
    ) -> dict[str, Any]:
        pr = create_pull_request(
            repo_full_name=repo_full_name,
            head=head,
            base=base,
            title=title,
            body=build_pr_body(summary=summary, validation=validation),
        )
        return {"number": pr.number, "url": pr.url, "title": pr.title}

    def answer_asset(self, request_id: str, answer: str) -> dict[str, str]:
        answer_asset_request(self.store, request_id, answer)
        return {"status": "resolved", "request_id": request_id}

    def capabilities(self) -> list[dict[str, Any]]:
        return [
            {
                "name": capability.name,
                "adapter_type": capability.adapter_type,
                "permissions": sorted(capability.permissions),
                "enabled": capability.enabled,
                "requires_approval": capability.requires_approval,
            }
            for capability in list_capabilities(self.store)
        ]

    def resource_status(self) -> dict[str, Any]:
        status = check_resources(self.config.safety)
        return {
            "safe_for_local": status.safe_for_local,
            "hard_stop": status.hard_stop,
            "messages": status.messages,
        }

    def index_memory(self) -> dict[str, Any]:
        entries = index_repo(self.store, self.config.repo_root)
        return {"indexed": len(entries)}

    def search_memory(self, query: str, limit: int = 5) -> list[dict[str, str]]:
        return [
            {"path": entry.path, "sha256": entry.sha256, "summary": entry.summary}
            for entry in search_memory(self.store, query, limit=limit)
        ]


def task_to_dict(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "type": task.type,
        "status": task.status,
        "risk": task.risk,
        "validation_profile": task.validation_profile,
        "model_provider": task.model_provider,
        "model_name": task.model_name,
        "retry_count": task.retry_count,
        "branch": task.branch,
        "commit_sha": task.commit_sha,
        "files_modified": task.files_modified,
        "result_summary": task.result_summary,
        "error_log": task.error_log,
    }
