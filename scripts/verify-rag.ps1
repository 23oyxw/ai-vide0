#Requires -Version 5.1
<#
.SYNOPSIS
  IntelliSafe-RAG + L8 写入 smoke test（v1.6 验证）
.DESCRIPTION
  覆盖 /rag/*、/report、/modules/l8-analytics/metrics、/webhooks/analytics
#>
param(
    [string]$BaseUrl = $(if ($env:ORCHESTRATOR_URL) { $env:ORCHESTRATOR_URL } else { "http://127.0.0.1:8765" })
)

$ErrorActionPreference = "Stop"
$passed = 0
$failed = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Method = "Get",
        [string]$Path,
        [object]$Body = $null,
        [scriptblock]$Assert
    )
    $uri = "$BaseUrl$Path"
    try {
        $params = @{ Uri = $uri; Method = $Method; ContentType = "application/json" }
        if ($null -ne $Body) {
            $params.Body = ($Body | ConvertTo-Json -Depth 8 -Compress)
        }
        $resp = Invoke-RestMethod @params
        if ($null -eq $resp.ok) { throw "Missing envelope 'ok'" }
        & $Assert $resp
        $script:passed++
        Write-Host "[PASS] $Name" -ForegroundColor Green
    }
    catch {
        $script:failed++
        Write-Host "[FAIL] $Name — $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "=== RAG + L8 Verify ===" -ForegroundColor Cyan
Write-Host "Target: $BaseUrl`n"

Test-Endpoint -Name "GET /rag/status" -Path "/rag/status" -Assert {
    param($r)
    if (-not $r.ok) { throw "ok=false" }
    if ($null -eq $r.data.stub_nodes) { throw "missing stub_nodes" }
}

Test-Endpoint -Name "POST /rag/ingest" -Method Post -Path "/rag/ingest" -Body @{
    source = "directory"
} -Assert {
    param($r)
    if (-not $r.ok) { throw "ok=false" }
    if ($r.data.nodes -lt 1) { throw "expected nodes >= 1" }
}

Test-Endpoint -Name "POST /rag/query" -Method Post -Path "/rag/query" -Body @{
    question = "种草视频开场钩子怎么写？"
    mode     = "auto"
} -Assert {
    param($r)
    if (-not $r.ok) { throw "ok=false" }
    if (-not $r.data.response) { throw "empty response" }
}

Test-Endpoint -Name "POST /rag/check" -Method Post -Path "/rag/check" -Body @{
    text = "本产品第一最好，联系手机13800138000"
} -Assert {
    param($r)
    if (-not $r.ok) { throw "ok=false" }
    if ($r.data.passed) { throw "expected compliance fail" }
}

Test-Endpoint -Name "POST /rag/estimate-cost" -Method Post -Path "/rag/estimate-cost" -Body @{
    source          = "directory"
    use_extractors  = $false
} -Assert {
    param($r)
    if (-not $r.ok) { throw "ok=false" }
    if ($r.data.total_estimated_tokens -lt 1) { throw "expected token estimate" }
}

Test-Endpoint -Name "GET /rag/kg/graph" -Path "/rag/kg/graph" -Assert {
    param($r)
    if (-not $r.ok) { throw "ok=false" }
    if ($null -eq $r.data.triplets) { throw "missing triplets" }
}

Test-Endpoint -Name "POST /rag/kg/query" -Method Post -Path "/rag/kg/query" -Body @{
    entity = "美妆"
} -Assert {
    param($r)
    if (-not $r.ok) { throw "ok=false" }
}

Test-Endpoint -Name "GET /report" -Path "/report?question=总结近期转化表现" -Assert {
    param($r)
    if (-not $r.ok) { throw "ok=false" }
    if (-not $r.data.summary) { throw "empty summary" }
}

Test-Endpoint -Name "GET /modules/l8-analytics/source" -Path "/modules/l8-analytics/source" -Assert {
    param($r)
    if (-not $r.ok) { throw "ok=false" }
    if (-not $r.data.source) { throw "missing source" }
}

$jobId = "verify-$(Get-Random -Maximum 99999)"
Test-Endpoint -Name "POST /modules/l8-analytics/metrics" -Method Post -Path "/modules/l8-analytics/metrics" -Body @{
    job_id         = $jobId
    clicks         = 1000
    unique_clicks  = 800
    conversions    = 80
    orders         = 40
    gmv            = 12000.0
} -Assert {
    param($r)
    if (-not $r.ok) { throw "ok=false" }
    if ($r.data.backend -notin @("sqlite", "postgres")) { throw "unexpected backend" }
}

Test-Endpoint -Name "POST /webhooks/analytics" -Method Post -Path "/webhooks/analytics" -Body @{
    job_id        = $jobId
    clicks        = 50
    unique_clicks = 40
    conversions   = 5
    orders        = 2
    gmv           = 599.0
} -Assert {
    param($r)
    if (-not $r.ok) { throw "ok=false" }
}

Test-Endpoint -Name "POST /pipeline/run (L1-L8 + RAG/L8 write)" -Method Post -Path "/pipeline/run" -Body @{
    product_url = "https://example.com/product/demo"
    layers      = @("L1", "L2", "L8")
} -Assert {
    param($r)
    if (-not $r.ok) { throw "ok=false" }
    if ($r.data.layer_results.Count -ne 3) { throw "expected 3 layers" }
    if ($r.data.status -ne "ok") { throw "pipeline not ok" }
}

Write-Host "`nPassed: $passed  Failed: $failed" -ForegroundColor Cyan
if ($failed -gt 0) { exit 1 }
exit 0
