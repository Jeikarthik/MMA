param(
    [string]$RepoRoot = "C:\Apps\MMA"
)

$ErrorActionPreference = "Stop"
$statePath = Join-Path $RepoRoot ".mma\run\processes.json"

if (-not (Test-Path -LiteralPath $statePath)) {
    Write-Host "No MMA process state found at $statePath"
    return
}

$processes = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
foreach ($entry in @($processes)) {
    $process = Get-Process -Id $entry.pid -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        Write-Host "$($entry.name) already stopped (PID $($entry.pid))."
        continue
    }
    Stop-Process -Id $entry.pid -Force
    Write-Host "Stopped $($entry.name) (PID $($entry.pid))."
}

Remove-Item -LiteralPath $statePath -Force
Write-Host "MMA stopped."
