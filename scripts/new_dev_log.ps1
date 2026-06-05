$date = Get-Date -Format "yyyy-MM-dd"
$root = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $root "dev-logs"
$logPath = Join-Path $logDir "$date.md"

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
}

if (Test-Path $logPath) {
    Write-Host "今日开发日志已存在: $logPath"
    exit 0
}

$content = @"
# $date 开发日志

## 今日目标

- 

## 完成事项

- 

## 验证结果

- 

## 待办事项

- 

## 风险与阻塞

- 
"@

Set-Content -LiteralPath $logPath -Value $content -Encoding UTF8
Write-Host "已创建今日开发日志: $logPath"
