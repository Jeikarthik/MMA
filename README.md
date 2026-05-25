# MMA

MMA is a local-first autonomous engineering orchestration prototype.

It implements the first useful loop from the PRD:

1. Accept one engineering task.
2. Store task state in SQLite.
3. Route ordinary work to local GGUF models and risky work to NVIDIA API.
4. Enforce hardware safety checks before local execution.
5. Produce patch-based changes.
6. Run stack-aware validation.
7. Commit passing work on a task branch.

The full product direction is documented in
[`AUTONOMOUS_ENGINEERING_ORCHESTRATION_SYSTEM_PRD_FINAL.md`](AUTONOMOUS_ENGINEERING_ORCHESTRATION_SYSTEM_PRD_FINAL.md).

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
mma init
mma new-task "Add a README section explaining local setup" --type doc
mma status
```

To enable NVIDIA API routing, set:

```powershell
$env:NVIDIA_API_KEY="..."
```

Local Ollama defaults to `http://localhost:11434`.

## MCP Server

MMA is intended to be used from VS Code, Cursor, Codex, Claude Code, or any MCP-compatible client.

Run the stdio MCP server:

```powershell
mma-mcp --repo C:\Apps\MMA
```

If running from source without installing:

```powershell
$env:PYTHONPATH="C:\Apps\MMA\src"
python -m mma.mcp_server --repo C:\Apps\MMA
```

Current MCP tools:

- `submit_task`
- `get_project_status`
- `get_task_detail`
- `run_task`
- `pause_task`
- `retry_task`
- `rollback_task`
- `get_diff`
- `answer_asset_request`
- `list_capabilities`
- `get_vram_status`
- `index_repo_memory`
- `search_repo_memory`
- `create_pull_request`

## Local HTTP API

For lightweight local integrations:

```powershell
mma-api --repo C:\Apps\MMA --port 8765
```

Endpoints include `/health`, `/tasks`, `/capabilities`, `/resources`, `/run`, and `/memory/index`.

## Safety

MMA never commits with `git add .`. It stages only files reported by a task result and runs validation before commit.

Critical or high-risk tasks skip weak local execution and route to NVIDIA API when available.

## Current Implementation Status

Implemented:

- SQLite task state and event log
- Local GGUF/NVIDIA routing rules
- Hardware safety checks
- Asset request blocking
- Capability registry for skills/plugins
- Patch extraction and application
- Stack-aware validation profiles
- Git branch, commit, diff, rollback helpers
- MCP stdio server
- Local HTTP API
- Lightweight repository memory
- Optional GitHub PR creation
- DPAPI-backed encrypted credential storage

Still intentionally staged for later hardening:

- Telegram bot
- Full DAG planner/executor
- Browser visual QA automation
- Production-grade prompt templates and repair memory
