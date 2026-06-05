$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$webDir = Join-Path $root "wenyuan-web"

Set-Location $webDir

if (-not (Test-Path -LiteralPath "node_modules")) {
    Write-Host "node_modules not found. Running npm install first."
    npm install
}

Write-Host "Starting wenyuan-web at http://127.0.0.1:5173"
npm run dev
