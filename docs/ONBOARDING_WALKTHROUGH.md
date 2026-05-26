# MMA Onboarding And Feature Walkthrough

This walkthrough teaches you how to start MMA, verify every major feature, and use it from the command line, Cursor/VS Code MCP, Telegram, and the local API.

## 1. First-Time Install

```powershell
cd C:\Apps\MMA
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
mma init
python -m pytest
```

Expected:

```text
48 passed
```

If the test count is higher, that is fine. It means more tests were added.

## 2. Configure Environment

For local Ollama:

```powershell
$env:OLLAMA_BASE_URL="http://localhost:11434"
```

For NVIDIA API:

```powershell
$env:NVIDIA_API_KEY="your_nvidia_key"
$env:NVIDIA_BASE_URL="https://integrate.api.nvidia.com/v1"
```

For Telegram:

```powershell
$env:TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
$env:TELEGRAM_ALLOWED_CHAT_IDS="your_chat_id"
```

For GitHub PR creation:

```powershell
$env:GITHUB_TOKEN="your_github_token"
```

Optional browser QA command:

```powershell
$env:MMA_BROWSER_QA_COMMAND="npm run test:e2e"
```

## 3. One-Command Startup

Start MMA services:

```powershell
cd C:\Apps\MMA
.\scripts\Start-MMA.ps1
```

This does all of the following:

- initializes MMA state
- runs an MCP smoke test
- starts the local HTTP API
- starts Telegram if `TELEGRAM_BOT_TOKEN` is set
- starts the watchdog loop
- writes logs to `.mma\logs`
- writes process state to `.mma\run\processes.json`

Check status:

```powershell
.\scripts\Status-MMA.ps1
```

Stop services:

```powershell
.\scripts\Stop-MMA.ps1
```

Important: Cursor/VS Code normally auto-starts the MCP stdio server from `mcp.cursor.json` or `.vscode\mcp.json`. The startup script runs an MCP smoke test, but it does not keep a detached MCP server running because MCP stdio servers are meant to be owned by the editor process.

## 4. Verify Provider Health

```powershell
mma provider-health
```

Check:

- Ollama availability
- NVIDIA key configured
- optional Claude key configured

## 5. Verify MCP Manually

```powershell
$env:PYTHONPATH="C:\Apps\MMA\src"
'{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python -m mma.mcp_server --repo C:\Apps\MMA
```

Expected:

- JSON response
- tools include `submit_task`, `run_task`, `submit_dag`, `get_provider_health`

## 6. Connect Cursor

Use `mcp.cursor.json`:

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

Add the `mma` server entry to Cursor's MCP config and restart Cursor.

## 7. Connect VS Code

Use:

```text
C:\Apps\MMA\.vscode\mcp.json
```

Restart VS Code after enabling MCP support.

## 8. Test CLI Task Flow

Create a docs task:

```powershell
mma new-task "Update README with a short note about MMA startup" --type doc
mma status
```

Run it:

```powershell
mma run TASK_ID
```

If the model needs context, MMA will create an asset request. Answer it with:

```powershell
mma answer-asset REQUEST_ID "the missing value or instruction"
```

## 9. Test Asset Blocking

Create a task that mentions an API key:

```powershell
mma new-task "Configure deploy with API key" --type config
mma status
```

Expected:

- task status becomes `awaiting_assets`
- MMA does not guess the key

## 10. Test Repo Memory

Index:

```powershell
mma index
```

Search:

```powershell
mma search-memory NVIDIA
```

Expected:

- summaries from matching files

## 11. Test DAG Flow

Create `dag.sample.json`:

```json
[
  {
    "key": "docs",
    "title": "Update docs",
    "description": "Update README",
    "type": "doc"
  },
  {
    "key": "review",
    "title": "Review docs",
    "description": "Review README update",
    "type": "doc",
    "depends_on": ["docs"]
  }
]
```

Create the DAG:

```powershell
mma create-dag dag.sample.json
mma status
```

Run dependency-ready tasks:

```powershell
mma run-pending --limit 1
```

## 12. Test Capabilities / Skills / Plugins

List:

```powershell
mma capabilities
```

Expected:

- `repo-inspect` is read-only
- `browser-qa` requires approval
- `github-pr` requires approval

Through MCP, use:

- `list_capabilities`
- `invoke_capability`

Read-only repo inspection can run without approval. Browser QA and GitHub actions require approval.

## 13. Test Browser QA Hook

Without config:

```powershell
python -m pytest tests\test_browser_qa.py
```

Expected:

- it confirms browser QA fails safely when no command is configured

With config:

```powershell
$env:MMA_BROWSER_QA_COMMAND="python -c `"print('browser ok')`""
```

Then invoke `browser-qa` through MCP with approval.

## 14. Test Telegram

Start:

```powershell
.\scripts\Start-MMA.ps1
```

In Telegram:

```text
/start
/status
/new_task Update docs
/run TASK_ID
/retry TASK_ID
/pause TASK_ID
/resources
/provider_health
```

Do not run without `TELEGRAM_ALLOWED_CHAT_IDS`.

## 15. Test Local HTTP API

After startup:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
Invoke-RestMethod http://127.0.0.1:8765/tasks
Invoke-RestMethod http://127.0.0.1:8765/resources
```

Create task through HTTP:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8765/tasks `
  -ContentType "application/json" `
  -Body '{"description":"Update docs through API","task_type":"doc"}'
```

## 16. Test Secret Storage

```powershell
mma set-secret NVIDIA_API_KEY "example-secret"
mma get-secret NVIDIA_API_KEY
```

Expected:

```text
NVIDIA_API_KEY is stored
```

## 17. Test Secret Scan

The commit path blocks obvious secrets. The automated test is:

```powershell
python -m pytest tests\test_security.py
```

## 18. Test Watchdog

```powershell
mma watchdog --stale-minutes 30
```

Expected:

- JSON report
- stale tasks if any
- resource safety messages if any

## 19. Test GitHub PR Helper

Set:

```powershell
$env:GITHUB_TOKEN="your_token"
```

Use the MCP tool:

```text
create_pull_request
```

Required fields:

- `repo_full_name`
- `head`
- `title`
- `summary`
- `validation`

## 20. Daily Use Flow

Normal day:

```powershell
cd C:\Apps\MMA
.\scripts\Start-MMA.ps1
```

Then open Cursor or VS Code. The editor should start MCP from config.

At the end:

```powershell
.\scripts\Stop-MMA.ps1
```

If you only want editor MCP and not Telegram/API:

```powershell
.\scripts\Start-MMA.ps1 -NoTelegram -NoApi
```

## 21. Troubleshooting

SQLite disk I/O error under `C:\Apps`:

- run PowerShell with permission to write to `C:\Apps\MMA`, or
- move MMA to a user-writable folder.

MCP does not show in Cursor/VS Code:

- confirm `PYTHONPATH=C:\Apps\MMA\src`
- run the MCP smoke test manually
- restart the editor

Telegram does not respond:

- check `.mma\logs\telegram.log`
- verify `TELEGRAM_BOT_TOKEN`
- verify `TELEGRAM_ALLOWED_CHAT_IDS`

NVIDIA calls fail:

- run `mma provider-health`
- verify `NVIDIA_API_KEY`
- verify model names in `src\mma\config.py`

Browser QA fails:

- configure `MMA_BROWSER_QA_COMMAND`
- make sure the command works manually in the target project.
