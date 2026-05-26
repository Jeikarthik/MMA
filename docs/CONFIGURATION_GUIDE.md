# MMA Configuration Guide

This guide covers everything that cannot be completed automatically by the repo itself because it depends on your local machine, API keys, or editor settings.

## 1. Install MMA

```powershell
cd C:\Apps\MMA
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
mma init
python -m pytest
```

Expected test result:

```text
48 passed
```

## 2. Configure Local Ollama

MMA expects Ollama at:

```powershell
$env:OLLAMA_BASE_URL="http://localhost:11434"
```

Check available models:

```powershell
ollama list
mma provider-health
```

Recommended local roles from the PRD:

- simple tasks: Gemma 4 uncensored GGUF
- coding: Qwen2.5-Coder 7B GGUF
- planning fallback: Hermes 3 8B GGUF or smaller safe model
- vision: Qwen2.5-VL 7B GGUF
- embeddings: nomic-embed-text

Model names are configured in `src\mma\config.py`. If your local Ollama model names differ, update the defaults there or add environment-driven config later.

## 3. Configure NVIDIA API

Set your NVIDIA key for the current PowerShell session:

```powershell
$env:NVIDIA_API_KEY="your_key_here"
$env:NVIDIA_BASE_URL="https://integrate.api.nvidia.com/v1"
```

Or store it encrypted in Windows DPAPI:

```powershell
mma set-secret NVIDIA_API_KEY "your_key_here"
mma get-secret NVIDIA_API_KEY
```

Note: current provider calls read `NVIDIA_API_KEY` from the environment. DPAPI storage is implemented for safe local storage; automatic injection from the encrypted store can be added if you want no env vars.

Verify:

```powershell
mma provider-health
```

## 4. Configure MCP For Cursor

Use `mcp.cursor.json` as the server definition:

```json
{
  "mcpServers": {
    "mma": {
      "command": "python",
      "args": ["-m", "mma.mcp_server", "--repo", "C:\\Apps\\MMA"],
      "env": {
        "PYTHONPATH": "C:\\Apps\\MMA\\src"
      }
    }
  }
}
```

Add this entry to Cursor's MCP configuration, then restart Cursor.

## 5. Configure MCP For VS Code

The repo includes:

```text
C:\Apps\MMA\.vscode\mcp.json
```

It launches:

```powershell
python -m mma.mcp_server --repo C:\Apps\MMA
```

with:

```powershell
PYTHONPATH=C:\Apps\MMA\src
```

## 6. MCP Smoke Test

Run:

```powershell
$env:PYTHONPATH="C:\Apps\MMA\src"
'{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python -m mma.mcp_server --repo C:\Apps\MMA
```

Expected result:

- JSON-RPC response
- contains tools like `submit_task`, `run_task`, `submit_dag`, `get_provider_health`

If you see a SQLite disk I/O error under `C:\Apps`, run the shell as a user with write permission to `C:\Apps\MMA` or move MMA to a non-protected folder.

## 7. Configure Telegram

Create a Telegram bot with BotFather, then set:

```powershell
$env:TELEGRAM_BOT_TOKEN="your_bot_token"
$env:TELEGRAM_ALLOWED_CHAT_IDS="your_chat_id"
mma-telegram --repo C:\Apps\MMA
```

Use an allowlist. Do not run Telegram control without `TELEGRAM_ALLOWED_CHAT_IDS`.

Commands:

- `/start`
- `/new_task describe the task`
- `/status`
- `/run TASK_ID`
- `/retry TASK_ID`
- `/rollback TASK_ID`
- `/pause TASK_ID`
- `/answer_asset REQUEST_ID answer text`
- `/capabilities`
- `/resources`
- `/provider_health`

## 8. Configure GitHub

For PR creation:

```powershell
$env:GITHUB_TOKEN="github_pat_or_token"
```

The token needs permission to create pull requests in `Jeikarthik/MMA`.

MMA can create PRs through the MCP tool:

```text
create_pull_request
```

## 9. Configure Browser QA

Browser QA is a safe command hook. It does not assume a browser runner until you provide one.

Example:

```powershell
$env:MMA_BROWSER_QA_COMMAND="npm run test:e2e"
```

If your app URL is needed, MMA passes it as:

```powershell
$env:MMA_BROWSER_QA_URL
```

If `MMA_BROWSER_QA_COMMAND` is not configured, browser QA fails safely instead of pretending it passed.

## 10. Run The Watchdog

Manual:

```powershell
mma watchdog --stale-minutes 30
```

For periodic checks, create a Windows Task Scheduler job that runs the same command from `C:\Apps\MMA`.

## 11. Basic Workflow

Create a task:

```powershell
mma new-task "Update README with NVIDIA setup" --type doc
mma status
```

Run a task:

```powershell
mma run TASK_ID
```

Run dependency-ready pending tasks:

```powershell
mma run-pending --limit 1
```

Index memory:

```powershell
mma index
mma search-memory NVIDIA
```

## 12. What You Still Must Provide Manually

MMA cannot invent or safely configure these:

- NVIDIA API key
- Telegram bot token
- Telegram chat ID allowlist
- GitHub token for PR creation
- exact local Ollama model names if they differ from defaults
- browser QA command for your frontend stack
- any real project assets, secrets, brand files, screenshots, business rules, or deployment credentials

The system is designed to ask for these instead of guessing.
