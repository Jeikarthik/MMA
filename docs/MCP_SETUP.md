# MMA MCP Setup

MMA exposes the orchestration system through a stdio MCP server.

## Cursor

Copy `mcp.cursor.json` into your Cursor MCP configuration or merge the `mma` server entry into your existing config.

## VS Code

Use `.vscode/mcp.json` from this repository. It launches:

```powershell
python -m mma.mcp_server --repo C:\Apps\MMA
```

with:

```powershell
PYTHONPATH=C:\Apps\MMA\src
```

## Smoke Test

From PowerShell:

```powershell
$env:PYTHONPATH="C:\Apps\MMA\src"
'{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python -m mma.mcp_server --repo C:\Apps\MMA
```

You should receive a JSON-RPC response containing MMA tools such as `submit_task`, `run_task`, and `get_project_status`.

## Important Tools

- `submit_task`: create one task.
- `submit_dag`: create dependent tasks.
- `run_task`: execute a task.
- `get_project_status`: list tasks.
- `answer_asset_request`: provide missing context.
- `get_provider_health`: check Ollama/NVIDIA configuration.
- `index_repo_memory`: refresh repo memory.
- `search_repo_memory`: query indexed context.
