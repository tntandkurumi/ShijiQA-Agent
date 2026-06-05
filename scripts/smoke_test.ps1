param(
    [switch]$SkipFrontendBuild
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$apiDir = Join-Path $root "wenyuan-api"
$webDir = Join-Path $root "wenyuan-web"

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

Write-Host "== Backend import check =="
Push-Location $apiDir
try {
    & $python -c "import app.main; print('app import ok')"
    Write-Host "== Prepared retrieval check =="
    $retrievalCheck = @'
from app.services.prepared_retrieval import execute_prepared_tool

tests = [
    ("search_person", {"query": "\u9648\u9738\u5148"}),
    ("search_poetry", {"author": "\u9648\u53d4\u5b9d"}),
    ("search_official_positions", {"query": "\u4e1e\u76f8"}),
    ("search_geography", {"query": "\u5efa\u5eb7"}),
    ("search_historical_events", {"query": "\u4faf\u666f\u4e4b\u4e71"}),
    ("search_terminology", {"query": "\u8df5\u795a"}),
    ("search_knowledge_graph", {"query": "\u9648\u9738\u5148"}),
    ("search_bilingual", {"query": "\u9648\u9738\u5148\u53d7\u7985\u5efa\u7acb\u9648\u671d"}),
]

for name, args in tests:
    result = execute_prepared_tool(name, args, "")
    if not result.raw_text:
        raise RuntimeError(f"{name} returned empty raw text")
    if not result.chunks:
        raise RuntimeError(f"{name} returned no chunks")
print("prepared retrieval ok")
'@
    $retrievalCheck = "import sys`nsys.path.insert(0, r'$apiDir')`n" + $retrievalCheck
    $tmpRetrievalCheck = Join-Path $env:TEMP ("wenyuan_retrieval_check_" + [Guid]::NewGuid().ToString("N") + ".py")
    try {
        Set-Content -LiteralPath $tmpRetrievalCheck -Value $retrievalCheck -Encoding UTF8
        & $python $tmpRetrievalCheck
        if ($LASTEXITCODE -ne 0) {
            throw "Prepared retrieval check failed."
        }
    }
    finally {
        if (Test-Path -LiteralPath $tmpRetrievalCheck) {
            Remove-Item -LiteralPath $tmpRetrievalCheck -Force
        }
    }
}
finally {
    Pop-Location
}

$job = $null
$startedBackend = $false
Write-Host "== Preparing backend =="
try {
    $existingHealth = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -Method Get -TimeoutSec 2
    if ($existingHealth.status -eq "ok") {
        Write-Host "Reusing existing backend on port 8000"
    }
}
catch {
    Write-Host "Starting temporary backend"
    $job = Start-Job -ScriptBlock {
        param($jobApiDir, $jobPython)
        Set-Location -LiteralPath $jobApiDir
        & $jobPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000
    } -ArgumentList $apiDir, $python
    $startedBackend = $true
    Start-Sleep -Seconds 4
}

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -Method Get
    if ($health.status -ne "ok") {
        throw "Health check failed."
    }
    Write-Host "health ok"

    $username = "smoke_" + (Get-Random)
    $authBody = @{ username = $username; password = "123456" } | ConvertTo-Json
    $register = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/auth/register" -Method Post -ContentType "application/json" -Body $authBody
    if (-not $register.access_token) {
        throw "Register did not return token."
    }
    $headers = @{ Authorization = "Bearer " + $register.access_token }
    Write-Host "auth ok"

    $models = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/models" -Method Get -Headers $headers
    if ($models.Count -lt 1) {
        throw "Model list is empty."
    }
    Write-Host "models ok"

    $conversationBody = @{ title = "冒烟测试"; selected_model = "wenyuan-sim" } | ConvertTo-Json
    $conversation = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/conversations" -Method Post -ContentType "application/json" -Headers $headers -Body $conversationBody
    if (-not $conversation.id) {
        throw "Create conversation failed."
    }
    Write-Host "conversation ok"

    $chatBody = @{
        conversation_id = $conversation.id
        message = "Chen Baxian de shihao he Jian Chen guanxi shi shenme? Qing gei chu jiansuo yiju."
        model_name = "wenyuan-sim"
    } | ConvertTo-Json
    $stream = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8000/api/chat/stream" -Method Post -ContentType "application/json" -Headers $headers -Body $chatBody
    if (-not $stream.Content.Contains('"type": "done"')) {
        throw "SSE did not return done."
    }
    Write-Host "chat stream ok"

    $messages = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/conversations/$($conversation.id)/messages" -Method Get -Headers $headers
    if ($messages.Count -lt 2) {
        throw "Message history is insufficient."
    }
    Write-Host "messages ok"

    $runs = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/conversations/$($conversation.id)/agent-runs" -Method Get -Headers $headers
    if ($runs.Count -lt 1) {
        throw "Agent runs are empty."
    }
    if ($runs[0].process_blocks.Count -lt 1) {
        throw "Process blocks are empty."
    }
    Write-Host "agent runs ok"

    $deleteResult = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/conversations/$($conversation.id)" -Method Delete -Headers $headers
    if ($deleteResult.status -ne "deleted") {
        throw "Delete conversation failed."
    }
    Write-Host "delete conversation ok"
}
finally {
    if ($startedBackend -and $job) {
        Stop-Job $job -ErrorAction SilentlyContinue
        Remove-Job $job -Force -ErrorAction SilentlyContinue
    }
}

if (-not $SkipFrontendBuild) {
    Write-Host "== Frontend build =="
    Push-Location $webDir
    try {
        npm run build
    }
    finally {
        Pop-Location
    }
}

Write-Host "SMOKE TEST PASSED"
