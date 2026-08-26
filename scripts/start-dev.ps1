[CmdletBinding()]
param([int]$Port = 8000)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot 'venv\Scripts\python.exe'
$bundledNode = Join-Path $projectRoot 'node_bin\node-v22.14.0-win-x64\node.exe'
$node = if (Test-Path $bundledNode) { $bundledNode } else { 'node' }
$npm = if (Test-Path $bundledNode) { Join-Path $projectRoot 'node_bin\node-v22.14.0-win-x64\npm.cmd' } else { 'npm' }

if (-not (Test-Path $python)) { throw "Python virtual environment not found at $python. Create it and install requirements.txt first." }
if (-not (Test-Path (Join-Path $projectRoot 'pi_agent\node_modules\@earendil-works\pi-agent-core'))) {
    Write-Host '[dev] Installing Pi dependencies inside pi_agent/ ...'
    Push-Location (Join-Path $projectRoot 'pi_agent')
    try { & $npm ci } finally { Pop-Location }
}

$piPort = if ($env:PI_AGENT_PORT) { [int]$env:PI_AGENT_PORT } else { 8001 }
try {
    $existing = Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 "http://127.0.0.1:$piPort/health"
    if ($existing.StatusCode -eq 200) { throw "A service is already listening on Pi port $piPort. Stop it before running this launcher." }
} catch [System.Net.WebException] { }

$pi = Start-Process -FilePath $node -ArgumentList 'agent_service.js' -WorkingDirectory (Join-Path $projectRoot 'pi_agent') -WindowStyle Hidden -PassThru
try {
    $deadline = (Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 250
        if ($pi.HasExited) { throw "Pi Agent exited with code $($pi.ExitCode)." }
        try { $health = Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 "http://127.0.0.1:$piPort/health" } catch { $health = $null }
    } until (($health -and $health.StatusCode -eq 200) -or (Get-Date) -gt $deadline)
    if (-not $health) { throw 'Pi Agent did not become ready within 30 seconds.' }

    Write-Host "[dev] Pi Agent ready on $piPort. Starting FastAPI on $Port."
    Push-Location (Join-Path $projectRoot 'backend')
    try { & $python -m uvicorn app.main:app --host 127.0.0.1 --port $Port --reload } finally { Pop-Location }
} finally {
    if (-not $pi.HasExited) { Stop-Process -Id $pi.Id -Force }
}
