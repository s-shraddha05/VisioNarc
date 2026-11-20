# Start the Vite dev server on http://127.0.0.1:5173 (proxies /api to the backend).
# -Port serves on another port; -BackendOrigin proxies /api to another backend (default: frontend\.env).
param(
    [ValidateRange(1024, 65535)][int]$Port = 5173,
    [ValidatePattern('^(|https?://[^\s/]+)$')][string]$BackendOrigin = ''
)
$ErrorActionPreference = 'Stop'
$Frontend = Join-Path (Split-Path -Parent $PSScriptRoot) 'frontend'

# Preflight: one clear line per problem instead of an npm stack trace.
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host '[FAIL] npm was not found. Install Node.js 20 or later.' -ForegroundColor Red; exit 1
}
if (-not (Test-Path (Join-Path $Frontend 'node_modules'))) {
    Write-Host '[FAIL] frontend\node_modules is missing. Run scripts\bootstrap.ps1 first.' -ForegroundColor Red; exit 1
}
$busy = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($busy) {
    Write-Host "[FAIL] Port $Port is already in use by PID $($busy[0].OwningProcess). Stop the old server first." -ForegroundColor Red; exit 1
}
if (-not (Test-Path (Join-Path $Frontend 'public\mediapipe'))) {
    Write-Host '[WARN] MediaPipe files are not installed; face and motion capture will not work. Run scripts\setup_mediapipe.ps1.' -ForegroundColor Yellow
}

Push-Location $Frontend
$previousOrigin = $env:VITE_BACKEND_ORIGIN
try {
    if ($BackendOrigin) { $env:VITE_BACKEND_ORIGIN = $BackendOrigin }
    npm run dev -- --port $Port
} finally {
    # Restore, so running the script in an open PowerShell window does not change later runs.
    $env:VITE_BACKEND_ORIGIN = $previousOrigin
    Pop-Location
}
