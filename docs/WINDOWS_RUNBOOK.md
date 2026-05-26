# MMA Windows Runbook

## Install From Source

```powershell
cd C:\Apps\MMA
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
mma init
python -m pytest
```

## Configure Providers

```powershell
$env:OLLAMA_BASE_URL="http://localhost:11434"
$env:NVIDIA_API_KEY="..."
```

To store a credential encrypted with Windows DPAPI:

```powershell
mma set-secret NVIDIA_API_KEY "..."
```

## Run MCP

```powershell
$env:PYTHONPATH="C:\Apps\MMA\src"
python -m mma.mcp_server --repo C:\Apps\MMA
```

## Run Telegram

```powershell
$env:TELEGRAM_BOT_TOKEN="..."
$env:TELEGRAM_ALLOWED_CHAT_IDS="123456789"
mma-telegram --repo C:\Apps\MMA
```

## Run Watchdog

```powershell
mma watchdog --stale-minutes 30
```

Schedule this command with Windows Task Scheduler if you want periodic checks.
