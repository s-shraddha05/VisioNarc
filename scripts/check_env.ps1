<#
.SYNOPSIS
    VisoNarc - environment check. Read-only: installs nothing, changes nothing.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\check_env.ps1
#>
$ErrorActionPreference = 'Continue'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$script:Failures = 0
$script:Warnings = 0

function Write-Result([string]$Status, [string]$Name, [string]$Detail) {
    $color = switch ($Status) { 'OK' { 'Green' } 'WARN' { 'Yellow' } default { 'Red' } }
    if ($Status -eq 'FAIL') { $script:Failures++ }
    if ($Status -eq 'WARN') { $script:Warnings++ }
    Write-Host ("[{0,-4}] {1,-22} {2}" -f $Status, $Name, $Detail) -ForegroundColor $color
}

function Get-ToolVersion([string]$Command, [string[]]$Arguments) {
    $cmd = Get-Command $Command -ErrorAction SilentlyContinue
    if (-not $cmd) { return $null }
    try { return ((& $cmd.Source @Arguments 2>&1) | Out-String).Trim() } catch { return $null }
}

Write-Host ''
Write-Host 'VisoNarc - Drug Detection Using Voice and Motion' -ForegroundColor Cyan
Write-Host "Environment check for: $ProjectRoot" -ForegroundColor Cyan
Write-Host ''

# Python >= 3.11 (3.13 verified for every pinned dependency)
$py = Get-ToolVersion 'python' @('--version')
if ($py -match 'Python (\d+)\.(\d+)\.(\d+)') {
    $ver = [version]"$($Matches[1]).$($Matches[2]).$($Matches[3])"
    if ($ver -ge [version]'3.11') { Write-Result 'OK' 'Python' $py }
    else { Write-Result 'FAIL' 'Python' "$py (need 3.11 or newer)" }
} else { Write-Result 'FAIL' 'Python' 'python not found on PATH' }

# Node.js >= 20
$node = Get-ToolVersion 'node' @('--version')
if ($node -match 'v(\d+)\.(\d+)\.(\d+)') {
    if ([int]$Matches[1] -ge 20) { Write-Result 'OK' 'Node.js' $node }
    else { Write-Result 'FAIL' 'Node.js' "$node (need 20 or newer)" }
} else { Write-Result 'FAIL' 'Node.js' 'node not found on PATH' }

$npm = Get-ToolVersion 'npm' @('--version')
if ($npm) { Write-Result 'OK' 'npm' $npm } else { Write-Result 'FAIL' 'npm' 'npm not found on PATH' }

$git = Get-ToolVersion 'git' @('--version')
if ($git) { Write-Result 'OK' 'Git' $git } else { Write-Result 'WARN' 'Git' 'git not found (optional, recommended)' }

# MySQL 8 client + service
$mysql = Get-ToolVersion 'mysql' @('--version')
if (-not $mysql) {
    $default = 'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe'
    if (Test-Path $default) { $mysql = ((& $default --version) | Out-String).Trim() + '  (not on PATH)' }
}
if ($mysql -match 'Ver 8\.') { Write-Result 'OK' 'MySQL client' $mysql }
elseif ($mysql) { Write-Result 'WARN' 'MySQL client' "$mysql (MySQL 8 expected)" }
else { Write-Result 'FAIL' 'MySQL client' 'mysql.exe not found' }

$svc = Get-Service -Name 'MySQL*' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($svc -and $svc.Status -eq 'Running') { Write-Result 'OK' 'MySQL service' "$($svc.Name) is running" }
elseif ($svc) { Write-Result 'FAIL' 'MySQL service' "$($svc.Name) is $($svc.Status) - start it from services.msc" }
else { Write-Result 'WARN' 'MySQL service' 'no MySQL* Windows service found' }

# Disk space on the project drive
$drive = (Get-Item $ProjectRoot).PSDrive
$freeGb = [math]::Round($drive.Free / 1GB, 1)
if ($freeGb -ge 6) { Write-Result 'OK' 'Disk space' "$freeGb GB free on $($drive.Name):" }
elseif ($freeGb -ge 2) { Write-Result 'WARN' 'Disk space' "$freeGb GB free on $($drive.Name): (Phase 1 needs ~0.5 GB, Phase 3 AI libraries need ~1.5 GB more)" }
else { Write-Result 'FAIL' 'Disk space' "$freeGb GB free on $($drive.Name): (need at least 2 GB)" }

# Ports used by the dev servers
foreach ($port in 8000, 5173) {
    $busy = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($busy) { Write-Result 'WARN' "Port $port" "already in use by PID $($busy[0].OwningProcess)" }
    else { Write-Result 'OK' "Port $port" 'free' }
}

if ($ProjectRoot -match 'OneDrive') {
    Write-Result 'WARN' 'Project location' 'inside OneDrive - pause syncing or exclude .venv/node_modules to avoid file locks'
}

# Project files
$backendEnv = Join-Path $ProjectRoot 'backend\.env'
if (Test-Path $backendEnv) { Write-Result 'OK' 'backend\.env' 'present' }
else { Write-Result 'WARN' 'backend\.env' 'missing - run scripts\bootstrap.ps1' }

$venvPy = Join-Path $ProjectRoot 'backend\.venv\Scripts\python.exe'
if (Test-Path $venvPy) { Write-Result 'OK' 'Backend venv' 'present' }
else { Write-Result 'WARN' 'Backend venv' 'missing - run scripts\bootstrap.ps1' }

$nodeModules = Join-Path $ProjectRoot 'frontend\node_modules'
if (Test-Path $nodeModules) { Write-Result 'OK' 'Frontend packages' 'installed' }
else { Write-Result 'WARN' 'Frontend packages' 'missing - run scripts\bootstrap.ps1' }

Write-Host ''
Write-Host "Summary: $script:Failures failure(s), $script:Warnings warning(s)" -ForegroundColor Cyan
if ($script:Failures -gt 0) { exit 1 } else { exit 0 }
