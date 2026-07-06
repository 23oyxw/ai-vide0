#Requires -Version 5.1
<#
.SYNOPSIS
  一键验证：编排协议 + RAG/L8（需 orchestrator :8765 已启动）
#>
param(
    [string]$BaseUrl = $(if ($env:ORCHESTRATOR_URL) { $env:ORCHESTRATOR_URL } else { "http://127.0.0.1:8765" }),
    [switch]$SkipFullPipeline
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ErrorActionPreference = "Stop"

Write-Host "Checking $BaseUrl ..." -ForegroundColor Cyan
try {
    Invoke-RestMethod -Uri "$BaseUrl/health" -TimeoutSec 5 | Out-Null
}
catch {
    Write-Host "Orchestrator 未启动。请先运行:" -ForegroundColor Red
    Write-Host "  npm run dev:api" -ForegroundColor Yellow
    Write-Host "  或 scripts/start-dev.ps1" -ForegroundColor Yellow
    exit 1
}

if ($SkipFullPipeline) {
    & "$Root\verify-rag.ps1" -BaseUrl $BaseUrl
    exit $LASTEXITCODE
}

& "$Root\test_api_protocol.ps1" -BaseUrl $BaseUrl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& "$Root\verify-rag.ps1" -BaseUrl $BaseUrl
exit $LASTEXITCODE
