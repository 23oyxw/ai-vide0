#Requires -Version 5.1
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
        if ($null -ne $Body) { $params.Body = ($Body | ConvertTo-Json -Depth 8 -Compress) }
        $resp = Invoke-RestMethod @params
        if ($null -eq $resp.ok) { throw "Missing envelope.ok" }
        & $Assert $resp
        $script:passed++
        Write-Host "[PASS] $Name" -ForegroundColor Green
    }
    catch {
        $script:failed++
        Write-Host "[FAIL] $Name — $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "=== Module API Tests ===" -ForegroundColor Cyan

Test-Endpoint -Name "M1 POST /search" -Method Post -Path "/modules/l1-crawler/search" -Body @{
    keyword = "防晒"; vertical = "电商"; product_url = "https://example.com/p/demo"
} -Assert {
    param($r)
    if (-not $r.data.topics) { throw "expected topics" }
}

Test-Endpoint -Name "M1 GET /topics" -Path "/modules/l1-crawler/topics" -Assert {
    param($r)
    if ($r.meta.layer -ne "L1") { throw "expected L1" }
}

Test-Endpoint -Name "M2 POST /generate-script" -Method Post -Path "/modules/l2-content/generate-script" -Body @{
    topic = "平价护肤"; product_url = "https://example.com/p/1"
} -Assert {
    param($r)
    if ($r.data.script.segments.Count -ne 4) { throw "expected 4 segments" }
    $script:scriptId = $r.data.script.id
}

Test-Endpoint -Name "M3 POST /build-from-script" -Method Post -Path "/modules/l3-storyboard/build-from-script" -Body @{
    script_id = $scriptId; demo_name = "post_production_15s_zhongcao"
} -Assert {
    param($r)
    if (-not $r.data.storyboard.id) { throw "expected storyboard id" }
    $script:sbId = $r.data.storyboard.id
}

Test-Endpoint -Name "M4 POST /render" -Method Post -Path "/modules/l4-render/render" -Body @{
    storyboard_id = $sbId; demo_name = "post_production_15s_zhongcao"
} -Assert {
    param($r)
    if (-not $r.data.job.job_id) { throw "expected render job" }
    $script:renderId = $r.data.job.job_id
}

Test-Endpoint -Name "M4 GET /render/status" -Path "/modules/l4-render/render/$renderId/status" -Assert {
    param($r)
    if (-not $r.data.job.status) { throw "expected status" }
}

Test-Endpoint -Name "M5 POST /jobs" -Method Post -Path "/modules/l5-scheduler/jobs" -Body @{
    product_url = "https://example.com/p/1"
} -Assert {
    param($r)
    $script:jobId = $r.data.job.job_id
}

Test-Endpoint -Name "M5 GET /jobs" -Path "/modules/l5-scheduler/jobs" -Assert {
    param($r)
    if ($r.data.total -lt 1) { throw "expected jobs" }
}

Test-Endpoint -Name "M6 GET /rules" -Path "/modules/l6-qa/rules" -Assert {
    param($r)
    if ($r.data.prohibited_words.Count -lt 1) { throw "expected ban words" }
}

Test-Endpoint -Name "M6 POST /validate" -Method Post -Path "/modules/l6-qa/validate" -Body @{
    script_text = "这款护肤品质地很好，适合日常使用"
} -Assert {
    param($r)
    if ($null -eq $r.data.passed) { throw "expected passed flag" }
}

Test-Endpoint -Name "M7 POST /publish" -Method Post -Path "/modules/l7-publish/publish" -Body @{
    job_id = $jobId; title = "测试发布"
} -Assert {
    param($r)
    if (-not $r.data.published.utm_campaign) { throw "expected utm" }
}

Test-Endpoint -Name "M8 GET /dashboard" -Path "/modules/l8-analytics/dashboard" -Assert {
    param($r)
    if (-not $r.data.chart) { throw "expected echarts chart" }
}

Test-Endpoint -Name "M8 GET /analysis" -Path "/modules/l8-analytics/analysis" -Assert {
    param($r)
    if ($r.data.optimization_hints.Count -lt 1) { throw "expected hints" }
}

Test-Endpoint -Name "Pipeline /pipeline/run" -Method Post -Path "/pipeline/run" -Body @{
    product_url = "https://example.com/p/demo"
    layers = @("L1","L2","L3","L4","L5","L6","L7","L8")
} -Assert {
    param($r)
    if ($r.data.layer_results.Count -ne 8) { throw "expected 8 layer results via modules" }
}

Write-Host "`nPassed: $passed  Failed: $failed" -ForegroundColor Cyan
if ($failed -gt 0) { exit 1 }
