#Requires -Version 5.1
<#
.SYNOPSIS
  Full L1-L8 pipeline integration test against orchestrator :8765
#>
param(
    [string]$BaseUrl = $(if ($env:ORCHESTRATOR_URL) { $env:ORCHESTRATOR_URL } else { "http://127.0.0.1:8765" }),
    [switch]$ForceQaFail
)

$ErrorActionPreference = "Stop"

Write-Host "=== Full Pipeline Test (L1-L8) ===" -ForegroundColor Cyan
Write-Host "Target: $BaseUrl`n"

$body = @{
    product_url = "https://example.com/product/demo"
    topic       = "demo topic"
    script      = "hook -> pain -> product -> CTA"
    demo_name   = "post_production_15s_zhongcao"
    layers      = @("L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8")
}
if ($ForceQaFail) {
    $body.force_qa_fail = $true
    $body.layers = @("L1", "L2", "L3", "L4", "L5", "L6")
}

$resp = Invoke-RestMethod -Uri "$BaseUrl/pipeline/run" -Method Post -Body ($body | ConvertTo-Json -Depth 8) -ContentType "application/json"

if (-not $resp.ok) {
    Write-Host "FAIL: envelope ok=false" -ForegroundColor Red
    $resp | ConvertTo-Json -Depth 8
    exit 1
}

$data = $resp.data
Write-Host "job_id: $($data.job_id)" -ForegroundColor Green
Write-Host "status: $($data.status) pipeline_state: $($data.pipeline_state)"

$expectedLayers = $body.layers.Count
if ($data.layer_results.Count -ne $expectedLayers) {
    Write-Host "FAIL: expected $expectedLayers layer_results, got $($data.layer_results.Count)" -ForegroundColor Red
    exit 1
}

foreach ($lr in $data.layer_results) {
    $color = if ($lr.status -eq "ok") { "Green" } elseif ($lr.status -eq "skipped") { "Yellow" } else { "Red" }
    Write-Host "  $($lr.layer_id) $($lr.status): $($lr.message)" -ForegroundColor $color
}

if ($ForceQaFail) {
    if ($data.status -ne "qa_failed") {
        Write-Host "FAIL: expected qa_failed when force_qa_fail=true" -ForegroundColor Red
        exit 1
    }
    if ($data.retry_from -ne "L2") {
        Write-Host "FAIL: expected retry_from=L2" -ForegroundColor Red
        exit 1
    }
    Write-Host "`nforce_qa_fail path OK (retry_from=$($data.retry_from))" -ForegroundColor Green
    exit 0
}

if ($data.status -ne "ok") {
    Write-Host "FAIL: expected status=ok" -ForegroundColor Red
    if ($data.errors) { $data.errors | ForEach-Object { Write-Host "  error: $_" -ForegroundColor Red } }
    exit 1
}

$requiredArtifacts = @("storyboard_yaml", "manifest_path", "qa_score", "scheduled_job")
foreach ($key in $requiredArtifacts) {
    if (-not $data.artifacts.$key) {
        Write-Host "WARN: missing artifact $key" -ForegroundColor Yellow
    } else {
        Write-Host "artifact $key = $($data.artifacts.$key)" -ForegroundColor DarkGray
    }
}

if ($data.optimization_hints.Count -lt 1) {
    Write-Host "FAIL: expected optimization_hints from L8" -ForegroundColor Red
    exit 1
}

Write-Host "`nPASS: full L1-L8 pipeline" -ForegroundColor Green
exit 0
