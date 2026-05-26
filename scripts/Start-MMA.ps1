param(
    [string]$RepoRoot = "C:\Apps\MMA",
    [int]$ApiPort = 8765,
    [int]$WatchdogIntervalSeconds = 300,
    [switch]$NoApi,
    [switch]$NoTelegram,
    [switch]$NoWatchdog,
    [switch]$SkipMcpSmoke
)

$ErrorActionPreference = "Stop"

function Resolve-MmaPython {
    param([string]$Root)
    $venvPython = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) {
        return $venvPython
    }
    return "python"
}

function Start-MmaProcess {
    param(
        [string]$Name,
        [string]$Command,
        [string]$LogPath
    )
    $wrapped = @"
`$env:PYTHONPATH = "$RepoRoot\src"
Set-Location -LiteralPath "$RepoRoot"
$Command *> "$LogPath"
"@
    $process = Start-Process `
        -FilePath "powershell" `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $wrapped) `
        -WindowStyle Hidden `
        -PassThru
    [pscustomobject]@{
        name = $Name
        pid = $process.Id
        log = $LogPath
        started_at = (Get-Date).ToString("o")
    }
}

if (-not (Test-Path -LiteralPath $RepoRoot)) {
    throw "RepoRoot does not exist: $RepoRoot"
}

$python = Resolve-MmaPython -Root $RepoRoot
$runDir = Join-Path $RepoRoot ".mma\run"
$logDir = Join-Path $RepoRoot ".mma\logs"
New-Item -ItemType Directory -Force -Path $runDir, $logDir | Out-Null

$env:PYTHONPATH = "$RepoRoot\src"
Set-Location -LiteralPath $RepoRoot

& $python -m mma.cli init | Out-Host

if (-not $SkipMcpSmoke) {
    $mcpRequest = '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
    $mcpResponse = $mcpRequest | & $python -m mma.mcp_server --repo $RepoRoot
    if ($LASTEXITCODE -ne 0 -or $mcpResponse -notmatch "submit_task") {
        throw "MCP smoke test failed."
    }
    Write-Host "MCP smoke test passed. Cursor/VS Code can auto-start MCP from the provided config."
}

$processes = @()

if (-not $NoApi) {
    $apiLog = Join-Path $logDir "api.log"
    $processes += Start-MmaProcess `
        -Name "api" `
        -Command "& `"$python`" -m mma.http_api --repo `"$RepoRoot`" --port $ApiPort" `
        -LogPath $apiLog
    Write-Host "Started API on http://127.0.0.1:$ApiPort"
}

if (-not $NoTelegram) {
    if ([string]::IsNullOrWhiteSpace($env:TELEGRAM_BOT_TOKEN)) {
        Write-Host "Telegram not started: TELEGRAM_BOT_TOKEN is not set."
    } else {
        if ([string]::IsNullOrWhiteSpace($env:TELEGRAM_ALLOWED_CHAT_IDS)) {
            Write-Host "WARNING: TELEGRAM_ALLOWED_CHAT_IDS is not set. Set it before serious use."
        }
        $telegramLog = Join-Path $logDir "telegram.log"
        $processes += Start-MmaProcess `
            -Name "telegram" `
            -Command "& `"$python`" -m mma.telegram_bot --repo `"$RepoRoot`"" `
            -LogPath $telegramLog
        Write-Host "Started Telegram bot."
    }
}

if (-not $NoWatchdog) {
    $watchdogLog = Join-Path $logDir "watchdog.log"
    $watchdogCommand = @"
while (`$true) {
  & "$python" -m mma.cli --repo "$RepoRoot" watchdog
  Start-Sleep -Seconds $WatchdogIntervalSeconds
}
"@
    $processes += Start-MmaProcess -Name "watchdog" -Command $watchdogCommand -LogPath $watchdogLog
    Write-Host "Started watchdog loop every $WatchdogIntervalSeconds seconds."
}

$statePath = Join-Path $runDir "processes.json"
$processes | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statePath -Encoding UTF8

Write-Host ""
Write-Host "MMA startup complete."
Write-Host "Process state: $statePath"
Write-Host "Logs: $logDir"
Write-Host "Run scripts\Status-MMA.ps1 to inspect, scripts\Stop-MMA.ps1 to stop."
