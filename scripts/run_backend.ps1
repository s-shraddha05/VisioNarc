# Start the FastAPI backend on http://127.0.0.1:8000 (auto-reload on code changes).
# -Port runs a second copy on another port (for example to test without stopping the first).
param([ValidateRange(1024, 65535)][int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$Backend = Join-Path (Split-Path -Parent $PSScriptRoot) 'backend'
$Python = Join-Path $Backend '.venv\Scripts\python.exe'

# Preflight: one clear line per problem instead of a traceback.
if (-not (Test-Path $Python)) {
    Write-Host '[FAIL] backend\.venv is missing. Run scripts\bootstrap.ps1 first.' -ForegroundColor Red; exit 1
}
$busy = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($busy) {
    Write-Host "[FAIL] Port $Port is already in use by PID $($busy[0].OwningProcess). Stop the old server first." -ForegroundColor Red; exit 1
}

Push-Location $Backend
try {
    & $Python -m scripts.preflight
    if ($LASTEXITCODE -ne 0) { Write-Host 'Fix the problem above, then run this script again.' -ForegroundColor Red; exit 1 }
    & $Python -m uvicorn app.main:app --host 127.0.0.1 --port $Port --reload --reload-dir app
} finally { Pop-Location }
