$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$apiDir = Join-Path $root "wenyuan-api"

function Resolve-WenyuanPython {
    if ($env:WENYUAN_PYTHON -and (Test-Path -LiteralPath $env:WENYUAN_PYTHON)) {
        return $env:WENYUAN_PYTHON
    }
    $userPython = Join-Path ([Environment]::GetFolderPath("UserProfile")) "venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $userPython) {
        return $userPython
    }
    $candidate = Get-ChildItem -LiteralPath "C:\Users" -Directory -ErrorAction SilentlyContinue |
        ForEach-Object { Join-Path $_.FullName "venv\Scripts\python.exe" } |
        Where-Object { Test-Path -LiteralPath $_ } |
        Select-Object -First 1
    if ($candidate) {
        return $candidate
    }
    throw "Python interpreter not found. Set WENYUAN_PYTHON to the existing python.exe path."
}

$python = Resolve-WenyuanPython

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python interpreter not found: $python"
}

Set-Location $apiDir
Write-Host "Starting wenyuan-api at http://127.0.0.1:8000"
& $python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
