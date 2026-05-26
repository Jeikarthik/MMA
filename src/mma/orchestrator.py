"""Single-task orchestration loop."""

from __future__ import annotations

from dataclasses import dataclass

from mma.context import assemble_context
from mma.config import AppConfig
from mma.db import Store, Task
from mma.assets import create_asset_request
from mma.failures import classify_failure
from mma.git_ops import changed_files_from_patch, commit_files, ensure_branch
from mma.locks import acquire_file_locks, release_file_locks
from mma.patches import PatchError, apply_patch, extract_unified_diff
from mma.providers import ProviderError, generate
from mma.resources import check_resources
from mma.routing import choose_route
from mma.validation import run_validation


@dataclass(frozen=True)
class RunResult:
    task_id: str
    status: str
    message: str


class Orchestrator:
    def __init__(self, config: AppConfig, store: Store) -> None:
        self.config = config
        self.store = store

    def run_task(self, task_id: str, *, model_override: str | None = None) -> RunResult:
        task = self.store.get_task(task_id)
        if task is None:
            raise ValueError(f"task not found: {task_id}")

        self.store.transition(task.id, "scouting")
        resource_status = check_resources(self.config.safety)
        route = choose_route(task, self.config, local_safe=resource_status.safe_for_local, override=model_override)
        self.store.update_task(task.id, model_provider=route.provider, model_name=route.model)

        if route.provider == "local" and not resource_status.safe_for_local:
            self.store.transition(task.id, "awaiting_approval", {"reason": "local resources unsafe"})
            return RunResult(task.id, "awaiting_approval", "; ".join(resource_status.messages))

        branch = f"task/{task.id[:8]}-{_slug(task.title)}"
        self.store.update_task(task.id, branch=branch)
        self.store.transition(task.id, "executing", {"provider": route.provider, "model": route.model})

        prompt = assemble_context(self.store, task).prompt
        try:
            ensure_branch(self.config.repo_root, branch)
            result = generate(route, self.config, prompt)
            self.store.log_usage(
                provider=route.provider,
                model=route.model,
                status="ok",
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
            if result.text.strip().startswith("NEEDS_CONTEXT:"):
                prompt = result.text.strip().split(":", 1)[1].strip()
                request_id = create_asset_request(self.store, task.id, prompt)
                return RunResult(
                    task.id,
                    "awaiting_assets",
                    f"Task needs context before continuing: {prompt} ({request_id})",
                )
            patch_text = extract_unified_diff(result.text)
            files = changed_files_from_patch(patch_text)
            acquire_file_locks(self.store, task.id, files)
            apply_patch(self.config.repo_root, patch_text, check=True)
            apply_patch(self.config.repo_root, patch_text, check=False)
        except (ProviderError, PatchError, RuntimeError) as exc:
            self._record_failure(task, str(exc))
            return RunResult(task.id, "failed", str(exc))

        self.store.update_task(task.id, files_modified=files)
        self.store.transition(task.id, "validating")
        validation = run_validation(self.config.repo_root, task.validation_profile)
        if not validation.passed:
            self._record_failure(task, validation.output)
            return RunResult(task.id, "failed", validation.output)

        try:
            commit_sha = commit_files(self.config.repo_root, files, _commit_message(task))
        except RuntimeError as exc:
            self.store.update_task(task.id, error_log=str(exc))
            self.store.transition(task.id, "failed", {"git": str(exc)})
            return RunResult(task.id, "failed", str(exc))

        self.store.update_task(
            task.id,
            commit_sha=commit_sha,
            result_summary=f"Committed {len(files)} file(s).",
        )
        self.store.transition(task.id, "complete")
        release_file_locks(self.store, task.id)
        return RunResult(task.id, "complete", f"Committed {len(files)} file(s) on {branch}.")

    def _record_failure(self, task: Task, output: str) -> None:
        retry_count = task.retry_count + 1
        diagnosis = classify_failure(output, retry_count=retry_count)
        status = "escalated" if diagnosis.escalate_to_nvidia and retry_count >= 2 else "failed"
        self.store.update_task(
            task.id,
            retry_count=retry_count,
            error_log=output,
            failure_digest=diagnosis.digest,
        )
        self.store.transition(
            task.id,
            status,
            {
                "failure_class": diagnosis.failure_class.value,
                "retryable": diagnosis.retryable,
                "escalate_to_nvidia": diagnosis.escalate_to_nvidia,
            },
        )
        release_file_locks(self.store, task.id)


def _slug(value: str) -> str:
    chars = [ch.lower() if ch.isalnum() else "-" for ch in value]
    slug = "".join(chars).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug[:40] or "task"


def _commit_message(task: Task) -> str:
    scope = task.type.replace("_", "-")
    return f"{scope}: {task.title[:60]}"
