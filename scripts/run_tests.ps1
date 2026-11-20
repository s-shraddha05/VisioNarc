<#
.SYNOPSIS
    Run all automated checks: backend pytest suite and frontend typecheck + production build.
    Add -MySql to also run the read-only checks against the real MySQL database.
#>
param([switch]$MySql)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$failed = @()

Push-Location (Join-Path $Root 'backend')
try {
    Write-Host '==> Backend tests' -ForegroundColor Cyan
    if ($MySql) { $env:VISONARC_TEST_MYSQL = '1' }
    & .\.venv\Scripts\python.exe -m pytest -q
    if ($LASTEXITCODE -ne 0) { $failed += 'backend tests' }
} finally {
    Remove-Item Env:VISONARC_TEST_MYSQL -ErrorAction SilentlyContinue
    Pop-Location
}

Push-Location (Join-Path $Root 'frontend')
try {
    Write-Host '==> Frontend unit tests (node --test)' -ForegroundColor Cyan
    npm test
    if ($LASTEXITCODE -ne 0) { $failed += 'frontend unit tests' }
    Write-Host '==> Frontend typecheck + build' -ForegroundColor Cyan
    npm run build
    if ($LASTEXITCODE -ne 0) { $failed += 'frontend build' }
} finally { Pop-Location }

if ($failed) { Write-Host "`nFAILED: $($failed -join ', ')" -ForegroundColor Red; exit 1 }
Write-Host "`nAll checks passed." -ForegroundColor Green
