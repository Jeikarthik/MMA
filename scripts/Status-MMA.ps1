param(
    [string]$RepoRoot = "C:\Apps\MMA"
)

$ErrorActionPreference = "Stop"
$statePath = Join-Path $RepoRoot ".mma\run\processes.json"

if (-not (Test-Path -LiteralPath $statePath)) {
    Write-Host "MMA is not currently tracked as running."
    return
}

$processes = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
foreach ($entry in @($processes)) {
    $process = Get-Process -Id $entry.pid -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        Write-Host "$($entry.name): stopped (PID $($entry.pid))"
    } else {
        Write-Host "$($entry.name): running (PID $($entry.pid)) log=$($entry.log)"
    }
}
