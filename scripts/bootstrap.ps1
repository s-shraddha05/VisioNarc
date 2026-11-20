<#
.SYNOPSIS
    VisoNarc - one-time project bootstrap. Safe to re-run (idempotent).

    1. Verifies the project structure and creates missing runtime folders.
    2. Creates backend\.env from .env.example with a freshly generated JWT secret (never overwrites).
    3. Creates the Python virtual environment backend\.venv and installs Phase 1 packages (~60 MB).
    4. Creates frontend\.env and installs frontend packages with npm ci (~150 MB).

    Changes no system settings and installs nothing outside this project folder.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
    powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 -SkipFrontend
#>
param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'

function Step([string]$Text) { Write-Host "`n==> $Text" -ForegroundColor Cyan }
function Ok([string]$Text) { Write-Host "    $Text" -ForegroundColor Green }

function New-RandomSecret([int]$Bytes = 48) {
    $buffer = New-Object byte[] $Bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buffer)
    return [Convert]::ToBase64String($buffer).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

function Invoke-Checked([string]$Exe, [string[]]$Arguments) {
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $Exe $($Arguments -join ' ')" }
}

Step 'Checking project structure'
$required = @(
    'backend\app\main.py', 'backend\requirements.txt', 'backend\alembic.ini',
    'backend\alembic\versions', 'frontend\package.json', 'frontend\src\main.tsx', 'docs'
)
$missing = $required | Where-Object { -not (Test-Path (Join-Path $Root $_)) }
if ($missing) { throw "Project files missing: $($missing -join ', '). Restore them before bootstrapping." }
foreach ($dir in 'backend\storage\tmp', 'backend\logs') {
    New-Item -ItemType Directory -Force -Path (Join-Path $Root $dir) | Out-Null
}
Ok 'Structure OK'

if (-not $SkipBackend) {
    Step 'Backend configuration (backend\.env)'
    $envFile = Join-Path $Backend '.env'
    if (Test-Path $envFile) {
        Ok '.env already exists - left unchanged'
    } else {
        $content = Get-Content (Join-Path $Backend '.env.example') -Raw
        $content = $content -replace '(?m)^JWT_SECRET_KEY=.*$', "JWT_SECRET_KEY=$(New-RandomSecret)"
        [IO.File]::WriteAllText($envFile, $content, (New-Object System.Text.UTF8Encoding $false))
        Ok '.env created with a new random JWT_SECRET_KEY (DB_PASSWORD is set by setup_mysql.ps1)'
    }

    Step 'Python virtual environment (backend\.venv)'
    $venvPy = Join-Path $Backend '.venv\Scripts\python.exe'
    if (-not (Test-Path $venvPy)) {
        Invoke-Checked 'python' @('-m', 'venv', (Join-Path $Backend '.venv'))
        Ok 'venv created'
    } else { Ok 'venv already exists' }
    Invoke-Checked $venvPy @('-m', 'pip', 'install', '--disable-pip-version-check', '-q', '-r', (Join-Path $Backend 'requirements-dev.txt'))
    Ok 'Backend packages installed'
}

if (-not $SkipFrontend) {
    Step 'Frontend configuration and packages'
    $feEnv = Join-Path $Frontend '.env'
    if (-not (Test-Path $feEnv)) { Copy-Item (Join-Path $Frontend '.env.example') $feEnv; Ok 'frontend\.env created' }
    Push-Location $Frontend
    try {
        if (Test-Path 'package-lock.json') { Invoke-Checked 'npm' @('ci', '--no-fund', '--no-audit') }
        else { Invoke-Checked 'npm' @('install', '--no-fund', '--no-audit') }
    } finally { Pop-Location }
    Ok 'Frontend packages installed'
}

Write-Host "`nBootstrap complete. Next: .\scripts\setup_mysql.ps1" -ForegroundColor Green
