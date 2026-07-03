#Requires -Version 5.1
<#
.SYNOPSIS
  End-to-end demo stub: setup -> health check -> pipeline run.
#>
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

Write-Host "=== Step 1: Tool verification ===" -ForegroundColor Cyan
& "$root\scripts\setup-tools.ps1"

Write-Host "`n=== Step 2: Python venv + deps ===" -ForegroundColor Cyan
if (-not (Test-Path "$root\.venv")) {
    python -m venv .venv
}
& "$root\.venv\Scripts\pip.exe" install -q -r requirements.txt
& "$root\.venv\Scripts\pip.exe" install -q -r mcp\c4d-mcp\requirements.txt

Write-Host "`n=== Step 3: Start orchestrator (background) ===" -ForegroundColor Cyan
$job = Start-Job -ScriptBlock {
    param($r)
    Set-Location $r
    & "$r\.venv\Scripts\python.exe" -m uvicorn orchestrator.main:app --host 127.0.0.1 --port 8765
} -ArgumentList $root

Start-Sleep -Seconds 3

Write-Host "`n=== Step 4: Health + Pipeline ===" -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8765/health" -Method Get
    Write-Host "Health: $($health | ConvertTo-Json -Compress)" -ForegroundColor Green

    $body = @{
        product_url = "https://example.com/product/demo"
        demo_name = "product_ad"
        layers = @("L1","L2","L3","L4","L5","L6","L7","L8")
    } | ConvertTo-Json

    $pipeline = Invoke-RestMethod -Uri "http://127.0.0.1:8765/pipeline/run" -Method Post -Body $body -ContentType "application/json"
    Write-Host "Pipeline job: $($pipeline.job_id) status=$($pipeline.status)" -ForegroundColor Green
    $pipeline.results | ForEach-Object { Write-Host "  $($_.layer_id) $($_.status): $($_.message)" }
} catch {
    Write-Host "API call failed: $_" -ForegroundColor Red
} finally {
    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -ErrorAction SilentlyContinue
}

Write-Host "`nDemo complete. Run manually: uvicorn orchestrator.main:app --reload --port 8765" -ForegroundColor Cyan
