"""Minimal MCP-compatible stdio server for editor clients.

This implements the JSON-RPC methods most MCP clients need first:
initialize, tools/list, and tools/call. It intentionally stays stdlib-only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Callable

from mma.services import MmaService


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "submit_task",
        "description": "Create a new MMA engineering task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "title": {"type": "string"},
                "task_type": {"type": "string"},
                "risk": {"type": "string", "enum": ["normal", "high", "auto"]},
                "validation_profile": {
                    "type": "string",
                    "enum": ["python", "frontend", "docs", "mixed", "generic", "auto"],
                },
            },
            "required": ["description"],
        },
    },
    {
        "name": "get_project_status",
        "description": "List MMA tasks and current state.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_task_detail",
        "description": "Get full task detail.",
        "inputSchema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
        },
    },
    {
        "name": "run_task",
        "description": "Run a task through routing, validation, and Git commit.",
        "inputSchema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}, "model": {"type": "string"}},
            "required": ["task_id"],
        },
    },
    {
        "name": "pause_task",
        "description": "Pause a task.",
        "inputSchema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
        },
    },
    {
        "name": "retry_task",
        "description": "Reset a failed/paused task to pending.",
        "inputSchema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
        },
    },
    {
        "name": "rollback_task",
        "description": "Revert the commit produced by a task.",
        "inputSchema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
        },
    },
    {
        "name": "get_diff",
        "description": "Return the committed diff for a task.",
        "inputSchema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
        },
    },
    {
        "name": "answer_asset_request",
        "description": "Answer a blocking asset/context request.",
        "inputSchema": {
            "type": "object",
            "properties": {"request_id": {"type": "string"}, "answer": {"type": "string"}},
            "required": ["request_id", "answer"],
        },
    },
    {
        "name": "list_capabilities",
        "description": "List enabled skills and plugins.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_vram_status",
        "description": "Return local resource safety status.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "index_repo_memory",
        "description": "Index repository files into MMA memory.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_repo_memory",
        "description": "Search indexed repository memory.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["query"],
        },
    },
    {
        "name": "create_pull_request",
        "description": "Create a GitHub pull request for a branch.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_full_name": {"type": "string"},
                "head": {"type": "string"},
                "base": {"type": "string"},
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "validation": {"type": "string"},
            },
            "required": ["repo_full_name", "head", "title", "summary", "validation"],
        },
    },
]


class JsonRpcServer:
    def __init__(self, service: MmaService) -> None:
        self.service = service

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        request_id = request.get("id")
        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "mma", "version": "0.1.0"},
                    "capabilities": {"tools": {}},
                }
            elif method == "tools/list":
                result = {"tools": TOOL_SCHEMAS}
            elif method == "tools/call":
                params = request.get("params") or {}
                result = self._call_tool(params.get("name"), params.get("arguments") or {})
            elif method == "notifications/initialized":
                return None
            else:
                return _error(request_id, -32601, f"method not found: {method}")
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except Exception as exc:  # noqa: BLE001 - JSON-RPC server must report all tool errors.
            return _error(request_id, -32000, str(exc))

    def _call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "submit_task": lambda a: self.service.create_task(
                description=a["description"],
                title=a.get("title"),
                task_type=a.get("task_type", "code"),
                risk=a.get("risk", "auto"),
                validation_profile=a.get("validation_profile", "auto"),
            ),
            "get_project_status": lambda _a: self.service.list_tasks(),
            "get_task_detail": lambda a: self.service.get_task(a["task_id"]),
            "run_task": lambda a: self.service.run_task(a["task_id"], a.get("model")),
            "pause_task": lambda a: self.service.pause_task(a["task_id"]),
            "retry_task": lambda a: self.service.retry_task(a["task_id"]),
            "rollback_task": lambda a: self.service.rollback_task(a["task_id"]),
            "get_diff": lambda a: self.service.get_diff(a["task_id"]),
            "answer_asset_request": lambda a: self.service.answer_asset(a["request_id"], a["answer"]),
            "list_capabilities": lambda _a: self.service.capabilities(),
            "get_vram_status": lambda _a: self.service.resource_status(),
            "index_repo_memory": lambda _a: self.service.index_memory(),
            "search_repo_memory": lambda a: self.service.search_memory(a["query"], a.get("limit", 5)),
            "create_pull_request": lambda a: self.service.create_pr(
                repo_full_name=a["repo_full_name"],
                head=a["head"],
                base=a.get("base", "main"),
                title=a["title"],
                summary=a["summary"],
                validation=a["validation"],
            ),
        }
        if name not in handlers:
            raise ValueError(f"unknown tool: {name}")
        payload = handlers[name](args)
        return {"content": [{"type": "text", "text": json.dumps(payload, indent=2)}]}


def serve(repo: Path) -> int:
    service = MmaService(repo)
    service.init()
    server = JsonRpcServer(service)
    for line in sys.stdin:
        if not line.strip():
            continue
        response = server.handle(json.loads(line))
        if response is not None:
            print(json.dumps(response), flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mma-mcp")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    return serve(Path(args.repo))


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


if __name__ == "__main__":
    raise SystemExit(main())
