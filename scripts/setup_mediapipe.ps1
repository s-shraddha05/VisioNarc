<#
.SYNOPSIS
    VisoNarc - install the browser-side MediaPipe assets used by the Face and Motion pages.

    1. Copies the MediaPipe Tasks Vision WebAssembly runtime (SIMD + non-SIMD builds, ~25 MB)
       from frontend\node_modules into frontend\public\mediapipe\wasm.
    2. Downloads two official MediaPipe models (~9 MB total) from Google's model storage into
       frontend\public\mediapipe\models and verifies their SHA-256 checksums.

    The assets are served by Vite from /mediapipe/... and are git-ignored. Safe to re-run.
    Run scripts\bootstrap.ps1 (npm ci) first so node_modules exists.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\setup_mediapipe.ps1
#>
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root 'frontend'
$Source = Join-Path $Frontend 'node_modules\@mediapipe\tasks-vision\wasm'
$Target = Join-Path $Frontend 'public\mediapipe'

# Apache-2.0 models published by Google for MediaPipe Tasks (see docs/ARCHITECTURE.md).
$Models = @(
    @{
        Name   = 'face_landmarker.task'
        Url    = 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task'
        Sha256 = '64184E229B263107BC2B804C6625DB1341FF2BB731874B0BCC2FE6544E0BC9FF'
    },
    @{
        Name   = 'pose_landmarker_lite.task'
        Url    = 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task'
        Sha256 = '59929E1D1EE95287735DDD833B19CF4AC46D29BC7AFDDBBF6753C459690D574A'
    }
)

if (-not (Test-Path $Source)) {
    throw "MediaPipe package not found at $Source. Run scripts\bootstrap.ps1 first."
}
$freeMb = [math]::Round((Get-PSDrive ((Get-Item $Root).PSDrive.Name)).Free / 1MB)
if ($freeMb -lt 300) { throw "Only $freeMb MB free on the project drive; at least 300 MB is required." }

Write-Host '==> Copying WebAssembly runtime' -ForegroundColor Cyan
$wasmDir = Join-Path $Target 'wasm'
New-Item -ItemType Directory -Force -Path $wasmDir | Out-Null
foreach ($f in 'vision_wasm_internal.js', 'vision_wasm_internal.wasm', 'vision_wasm_nosimd_internal.js', 'vision_wasm_nosimd_internal.wasm') {
    Copy-Item (Join-Path $Source $f) (Join-Path $wasmDir $f) -Force
}
Write-Host '    done' -ForegroundColor Green

Write-Host '==> Models' -ForegroundColor Cyan
$modelDir = Join-Path $Target 'models'
New-Item -ItemType Directory -Force -Path $modelDir | Out-Null
foreach ($m in $Models) {
    $path = Join-Path $modelDir $m.Name
    $ok = (Test-Path $path) -and ((Get-FileHash $path -Algorithm SHA256).Hash -eq $m.Sha256)
    if ($ok) { Write-Host "    $($m.Name) already present and verified"; continue }
    Write-Host "    downloading $($m.Name)"
    $tmp = "$path.part"
    Invoke-WebRequest -Uri $m.Url -OutFile $tmp -UseBasicParsing
    $hash = (Get-FileHash $tmp -Algorithm SHA256).Hash
    if ($hash -ne $m.Sha256) {
        Remove-Item $tmp -Force
        throw "Checksum mismatch for $($m.Name): got $hash, expected $($m.Sha256). File removed."
    }
    Move-Item $tmp $path -Force
    Write-Host "    $($m.Name) verified" -ForegroundColor Green
}
Write-Host "`nMediaPipe assets ready in frontend\public\mediapipe" -ForegroundColor Green
