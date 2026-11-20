<#
.SYNOPSIS
    VisoNarc - create the MySQL database and application user, then run migrations.

    - Prompts for the MySQL root password (hidden). It is written only to a temporary
      option file that is deleted immediately, and is never stored in the project.
    - Creates database `visonarc` (utf8mb4) and user `visonarc_app` limited to that database.
    - Generates a random password for visonarc_app and saves it in backend\.env (DB_PASSWORD).
    - Runs `alembic upgrade head` and `python -m scripts.verify_db`.

    Re-running is safe: the app user's password is rotated and .env updated.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\setup_mysql.ps1
#>
param(
    [string]$RootUser = 'root',
    [string]$MySqlHost = '127.0.0.1',
    [int]$Port = 3306,
    [string]$Database = 'visonarc',
    [string]$AppUser = 'visonarc_app'
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root 'backend'
$EnvFile = Join-Path $Backend '.env'
$VenvPy = Join-Path $Backend '.venv\Scripts\python.exe'

if (-not (Test-Path $EnvFile)) { throw 'backend\.env not found. Run scripts\bootstrap.ps1 first.' }
if (-not (Test-Path $VenvPy)) { throw 'backend\.venv not found. Run scripts\bootstrap.ps1 first.' }
if ($Database -notmatch '^[A-Za-z0-9_]+$' -or $AppUser -notmatch '^[A-Za-z0-9_]+$') {
    throw 'Database and user names may contain only letters, digits and underscores.'
}

$mysql = (Get-Command mysql -ErrorAction SilentlyContinue).Source
if (-not $mysql) { $mysql = 'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe' }
if (-not (Test-Path $mysql)) { throw 'mysql.exe not found. Add MySQL Server 8.0\bin to PATH.' }

$secure = Read-Host "MySQL password for '$RootUser'" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
$rootPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

# Alphanumeric only, so it needs no escaping in SQL, URLs or .env.
$chars = [char[]]'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$bytes = New-Object byte[] 32
$rng.GetBytes($bytes)
$appPassword = -join ($bytes | ForEach-Object { $chars[$_ % $chars.Length] })

$sql = @"
CREATE DATABASE IF NOT EXISTS ``$Database`` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS '$AppUser'@'localhost' IDENTIFIED BY '$appPassword';
CREATE USER IF NOT EXISTS '$AppUser'@'127.0.0.1' IDENTIFIED BY '$appPassword';
ALTER USER '$AppUser'@'localhost' IDENTIFIED BY '$appPassword';
ALTER USER '$AppUser'@'127.0.0.1' IDENTIFIED BY '$appPassword';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, INDEX, REFERENCES ON ``$Database``.* TO '$AppUser'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, INDEX, REFERENCES ON ``$Database``.* TO '$AppUser'@'127.0.0.1';
FLUSH PRIVILEGES;
SELECT 'database-ready' AS status;
"@

$optionFile = Join-Path $env:TEMP ("visonarc_mysql_{0}.cnf" -f [guid]::NewGuid().ToString('N'))
try {
    $escapedRoot = $rootPassword.Replace('\', '\\').Replace('"', '\"')
    [IO.File]::WriteAllText($optionFile, "[client]`nuser=$RootUser`npassword=`"$escapedRoot`"`nhost=$MySqlHost`nport=$Port`n")
    Write-Host "`n==> Creating database '$Database' and user '$AppUser'" -ForegroundColor Cyan
    $output = $sql | & $mysql "--defaults-extra-file=$optionFile" --batch --skip-column-names 2>&1
    if ($LASTEXITCODE -ne 0) { throw "MySQL setup failed:`n$($output | Out-String)" }
    if (($output | Out-String) -notmatch 'database-ready') { throw "Unexpected MySQL output:`n$($output | Out-String)" }
    Write-Host '    Database and user ready' -ForegroundColor Green
} finally {
    Remove-Item $optionFile -Force -ErrorAction SilentlyContinue
    $rootPassword = $null
}

Write-Host '==> Saving connection settings to backend\.env' -ForegroundColor Cyan
$envText = Get-Content $EnvFile -Raw
$updates = [ordered]@{ DB_HOST = $MySqlHost; DB_PORT = "$Port"; DB_NAME = $Database; DB_USER = $AppUser; DB_PASSWORD = $appPassword }
foreach ($key in $updates.Keys) {
    if ($envText -match "(?m)^$key=") { $envText = $envText -replace "(?m)^$key=.*$", "$key=$($updates[$key])" }
    else { $envText = $envText.TrimEnd() + "`n$key=$($updates[$key])`n" }
}
[IO.File]::WriteAllText($EnvFile, $envText, (New-Object System.Text.UTF8Encoding $false))
Write-Host '    backend\.env updated' -ForegroundColor Green

Push-Location $Backend
try {
    Write-Host '==> Applying migrations (alembic upgrade head)' -ForegroundColor Cyan
    & $VenvPy -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'alembic upgrade failed' }
    Write-Host '==> Verifying database' -ForegroundColor Cyan
    & $VenvPy -m scripts.verify_db
    if ($LASTEXITCODE -ne 0) { throw 'database verification failed' }
} finally { Pop-Location }

Write-Host "`nMySQL setup complete. Next: create an administrator:" -ForegroundColor Green
Write-Host '    cd backend; .\.venv\Scripts\python.exe -m scripts.create_admin --username admin'
