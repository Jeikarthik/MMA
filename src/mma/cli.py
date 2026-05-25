"""Command line interface for MMA."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from mma.assets import answer_asset_request
from mma.capabilities import list_capabilities, seed_default_capabilities
from mma.config import load_config
from mma.db import Store
from mma.memory import index_repo, search_memory
from mma.orchestrator import Orchestrator
from mma.scheduler import run_pending


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mma")
    parser.add_argument("--repo", default=".", help="repository root")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="initialize MMA state")

    new_task = sub.add_parser("new-task", help="create a task")
    new_task.add_argument("description")
    new_task.add_argument("--title")
    new_task.add_argument("--type", default="code")
    new_task.add_argument("--risk", choices=["normal", "high", "auto"], default="auto")
    new_task.add_argument(
        "--validation-profile",
        choices=["python", "frontend", "docs", "mixed", "generic", "auto"],
        default="auto",
    )

    sub.add_parser("status", help="list tasks")

    answer_asset = sub.add_parser("answer-asset", help="answer an asset/context request")
    answer_asset.add_argument("request_id")
    answer_asset.add_argument("answer")

    sub.add_parser("capabilities", help="list registered skills/plugins")

    sub.add_parser("index", help="index repository memory")

    search = sub.add_parser("search-memory", help="search repository memory")
    search.add_argument("query")

    pending = sub.add_parser("run-pending", help="run pending tasks sequentially")
    pending.add_argument("--limit", type=int, default=1)

    run = sub.add_parser("run", help="run a task")
    run.add_argument("task_id")
    run.add_argument("--model")

    pause = sub.add_parser("pause-task", help="pause a task")
    pause.add_argument("task_id")

    retry = sub.add_parser("retry", help="reset a task to pending")
    retry.add_argument("task_id")

    rollback = sub.add_parser("rollback", help="roll back a completed task commit")
    rollback.add_argument("task_id")

    diff = sub.add_parser("diff", help="show a task diff")
    diff.add_argument("task_id")

    secret_set = sub.add_parser("set-secret", help="store an encrypted credential")
    secret_set.add_argument("key")
    secret_set.add_argument("value")

    secret_get = sub.add_parser("get-secret", help="verify an encrypted credential exists")
    secret_get.add_argument("key")

    args = parser.parse_args(argv)
    config = load_config(Path(args.repo))
    store = Store(config.db_path)

    if args.command == "init":
        store.init()
        seed_default_capabilities(store)
        print(f"initialized {config.db_path}")
        return 0

    store.init()

    if args.command == "new-task":
        from mma.services import MmaService

        task = MmaService(config.repo_root).create_task(
            title=args.title,
            description=args.description,
            task_type=args.type,
            risk=args.risk,
            validation_profile=args.validation_profile,
        )
        print(task["id"])
        return 0

    if args.command == "status":
        for task in store.list_tasks():
            print(f"{task.id[:8]} {task.status:18} {task.type:10} {task.title}")
        return 0

    if args.command == "answer-asset":
        answer_asset_request(store, args.request_id, args.answer)
        print(f"resolved {args.request_id}")
        return 0

    if args.command == "capabilities":
        for capability in list_capabilities(store):
            approval = "approval-required" if capability.requires_approval else "read-only"
            print(f"{capability.name:16} {capability.adapter_type:10} {approval}")
        return 0

    if args.command == "index":
        entries = index_repo(store, config.repo_root)
        print(f"indexed {len(entries)} files")
        return 0

    if args.command == "search-memory":
        for entry in search_memory(store, args.query):
            print(f"{entry.path}: {entry.summary}")
        return 0

    if args.command == "run-pending":
        result = run_pending(config.repo_root, limit=args.limit)
        for run_result in result.results:
            print(f"{run_result.task_id[:8]} {run_result.status}: {run_result.message}")
        return 0 if all(item.status == "complete" for item in result.results) else 1

    if args.command == "run":
        result = Orchestrator(config, store).run_task(args.task_id, model_override=args.model)
        print(f"{result.status}: {result.message}")
        return 0 if result.status == "complete" else 1

    service = None
    if args.command in {"pause-task", "retry", "rollback", "diff"}:
        from mma.services import MmaService

        service = MmaService(config.repo_root)

    if args.command == "pause-task":
        print(service.pause_task(args.task_id)["status"])
        return 0

    if args.command == "retry":
        print(service.retry_task(args.task_id)["status"])
        return 0

    if args.command == "rollback":
        print(service.rollback_task(args.task_id)["status"])
        return 0

    if args.command == "diff":
        print(service.get_diff(args.task_id)["diff"])
        return 0

    if args.command == "set-secret":
        from mma.secrets import store_credential

        store_credential(store, args.key, args.value)
        print(f"stored {args.key}")
        return 0

    if args.command == "get-secret":
        from mma.secrets import load_credential

        load_credential(store, args.key)
        print(f"{args.key} is stored")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
