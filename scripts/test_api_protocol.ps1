#Requires -Version 5.1
<#
.SYNOPSIS
  Test unified API protocol against orchestrator on :8765
.DESCRIPTION
  Validates ok/data/error/meta envelope on all MASTER_PLAN FastAPI routes.
#>
param(
    [string]$BaseUrl = $(if ($env:ORCHESTRATOR_URL) { $env:ORCHESTRATOR_URL } else { "http://127.0.0.1:8765" })
)

$ErrorActionPreference = "Stop"
$passed = 0
$failed = 0
$results = @()

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Method = "Get",
        [string]$Path,
        [object]$Body = $null,
        [scriptblock]$Assert,
        [switch]$AllowErrorStatus
    )

    $uri = "$BaseUrl$Path"
    try {
        $params = @{
            Uri         = $uri
            Method      = $Method
            ContentType = "application/json"
        }
        if ($null -ne $Body) {
            $params.Body = ($Body | ConvertTo-Json -Depth 8 -Compress)
        }

        if ($AllowErrorStatus) {
            try {
                $resp = Invoke-RestMethod @params
            }
            catch {
                if ($_.ErrorDetails.Message) {
                    $resp = $_.ErrorDetails.Message | ConvertFrom-Json
                }
                elseif ($_.Exception.Response) {
                    $stream = $_.Exception.Response.GetResponseStream()
                    $reader = New-Object System.IO.StreamReader($stream)
                    $raw = $reader.ReadToEnd()
                    if ($raw) {
                        $resp = $raw | ConvertFrom-Json
                    }
                    else {
                        throw
                    }
                }
                else {
                    throw
                }
            }
        }
        else {
            $resp = Invoke-RestMethod @params
        }

        if ($null -eq $resp.ok) {
            throw "Missing envelope field 'ok'"
        }
        if (-not $resp.meta.timestamp) {
            throw "Missing envelope field 'meta.timestamp'"
        }

        & $Assert $resp

        $script:passed++
        $script:results += [pscustomobject]@{ Name = $Name; Result = "PASS"; Detail = "ok=$($resp.ok) layer=$($resp.meta.layer)" }
        Write-Host "[PASS] $Name" -ForegroundColor Green
    }
    catch {
        $script:failed++
        $msg = $_.Exception.Message
        $script:results += [pscustomobject]@{ Name = $Name; Result = "FAIL"; Detail = $msg }
        Write-Host "[FAIL] $Name — $msg" -ForegroundColor Red
    }
}

Write-Host "=== API Protocol Tests ===" -ForegroundColor Cyan
Write-Host "Target: $BaseUrl`n"

Test-Endpoint -Name "GET /health" -Path "/health" -Assert {
    param($r)
    if (-not $r.ok) { throw "expected ok=true" }
    if ($r.data.status -ne "ok") { throw "expected data.status=ok" }
    if (-not $r.data.layers) { throw "expected data.layers" }
}

Test-Endpoint -Name "GET /tools/check" -Path "/tools/check" -Assert {
    param($r)
    if (-not $r.ok) { throw "expected ok=true" }
    if (-not $r.data.video_factory) { throw "expected video_factory probe" }
}

Test-Endpoint -Name "GET /layers" -Path "/layers" -Assert {
    param($r)
    if (-not $r.ok) { throw "expected ok=true" }
    if (-not $r.data.L1) { throw "expected L1 in registry" }
}

Test-Endpoint -Name "GET /agent/crawler" -Path "/agent/crawler?product_url=https://example.com/p/demo" -Assert {
    param($r)
    if (-not $r.ok) { throw "expected ok=true" }
    if ($r.meta.layer -ne "L1") { throw "expected meta.layer=L1" }
    if (-not $r.data.crawled_url) { throw "expected crawled_url" }
}

Test-Endpoint -Name "POST /agent/crawler" -Method Post -Path "/agent/crawler" -Body @{
    product_url = "https://example.com/product/demo"
    competitor_urls = @("https://example.com/c/1")
} -Assert {
    param($r)
    if (-not $r.ok) { throw "expected ok=true" }
    if ($r.meta.layer -ne "L1") { throw "expected meta.layer=L1" }
    if (-not $r.data.selection_card) { throw "expected selection_card" }
}

Test-Endpoint -Name "GET /monitor" -Path "/monitor?job_id=test-job" -Assert {
    param($r)
    if (-not $r.ok) { throw "expected ok=true" }
    if ($r.meta.layer -ne "L6") { throw "expected meta.layer=L6" }
    if ($r.data.checks.Count -lt 1) { throw "expected checks array" }
}

Test-Endpoint -Name "POST /monitor" -Method Post -Path "/monitor" -Body @{
    job_id = "test-job"
    script_text = "demo script"
} -Assert {
    param($r)
    if (-not $r.ok) { throw "expected ok=true" }
    if ($r.meta.job_id -ne "test-job") { throw "expected meta.job_id=test-job" }
}

Test-Endpoint -Name "GET /data/click" -Path "/data/click?job_id=j1" -Assert {
    param($r)
    if (-not $r.ok) { throw "expected ok=true" }
    if ($r.meta.layer -ne "L8") { throw "expected meta.layer=L8" }
    if ($r.data.clicks -le 0) { throw "expected clicks > 0" }
}

Test-Endpoint -Name "POST /data/click" -Method Post -Path "/data/click" -Body @{
    job_id = "j1"
    utm_campaign = "seed"
} -Assert {
    param($r)
    if (-not $r.ok) { throw "expected ok=true" }
}

Test-Endpoint -Name "GET /data/conversion" -Path "/data/conversion" -Assert {
    param($r)
    if (-not $r.ok) { throw "expected ok=true" }
    if ($null -eq $r.data.conversion_rate) { throw "expected conversion_rate" }
}

Test-Endpoint -Name "POST /data/conversion" -Method Post -Path "/data/conversion" -Body @{
    job_id = "j1"
} -Assert {
    param($r)
    if (-not $r.ok) { throw "expected ok=true" }
}

Test-Endpoint -Name "GET /data/order" -Path "/data/order" -Assert {
    param($r)
    if (-not $r.ok) { throw "expected ok=true" }
    if ($r.data.orders -le 0) { throw "expected orders > 0" }
}

Test-Endpoint -Name "POST /data/order" -Method Post -Path "/data/order" -Body @{
    job_id = "j1"
} -Assert {
    param($r)
    if (-not $r.ok) { throw "expected ok=true" }
}

Test-Endpoint -Name "GET /data/analysis" -Path "/data/analysis?job_id=j1" -Assert {
    param($r)
    if (-not $r.ok) { throw "expected ok=true" }
    if ($r.data.optimization_hints.Count -lt 1) { throw "expected optimization_hints" }
}

Test-Endpoint -Name "POST /data/analysis" -Method Post -Path "/data/analysis" -Body @{
    job_id = "j1"
    metrics = @{ ctr = 0.04; cvr = 0.08 }
} -Assert {
    param($r)
    if (-not $r.ok) { throw "expected ok=true" }
    if ($r.data.feedback_targets.Count -lt 1) { throw "expected feedback_targets" }
}

Test-Endpoint -Name "POST /pipeline/run (L1-L3)" -Method Post -Path "/pipeline/run" -Body @{
    product_url = "https://example.com/product/demo"
    demo_name = "post_production_15s_zhongcao"
    layers = @("L1", "L2", "L3")
} -Assert {
    param($r)
    if (-not $r.ok) { throw "expected ok=true" }
    if ($r.meta.layer -ne "L5") { throw "expected meta.layer=L5" }
    if (-not $r.meta.job_id) { throw "expected meta.job_id" }
    if ($r.data.layer_results.Count -ne 3) { throw "expected 3 layer_results" }
    if ($r.data.status -ne "ok") { throw "expected data.status=ok" }
    if (-not $r.data.artifacts.storyboard_yaml) { throw "expected storyboard_yaml artifact" }
}

Test-Endpoint -Name "POST /pipeline/run (L1-L8 full)" -Method Post -Path "/pipeline/run" -Body @{
    product_url = "https://example.com/product/demo"
    demo_name = "post_production_15s_zhongcao"
    layers = @("L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8")
} -Assert {
    param($r)
    if (-not $r.ok) { throw "expected ok=true" }
    if ($r.data.layer_results.Count -ne 8) { throw "expected 8 layer_results" }
    if ($r.data.status -ne "ok") { throw "expected data.status=ok" }
    if (-not $r.data.artifacts.manifest_path) { throw "expected manifest_path" }
    if (-not $r.data.artifacts.qa_score) { throw "expected qa_score" }
}

Test-Endpoint -Name "POST /pipeline/run (force_qa_fail)" -Method Post -Path "/pipeline/run" -Body @{
    demo_name = "post_production_15s_zhongcao"
    layers = @("L1", "L2", "L3", "L4", "L5", "L6")
    force_qa_fail = $true
} -Assert {
    param($r)
    if (-not $r.ok) { throw "expected ok=true envelope" }
    if ($r.data.status -ne "qa_failed") { throw "expected qa_failed" }
    if ($r.data.retry_from -ne "L2") { throw "expected retry_from=L2" }
}

Test-Endpoint -Name "POST /pipeline/run (bad layer order)" -Method Post -Path "/pipeline/run" -Body @{
    layers = @("L3", "L1")
} -AllowErrorStatus -Assert {
    param($r)
    if ($r.ok) { throw "expected ok=false for bad order" }
    if (-not $r.error) { throw "expected error object" }
}

Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "Passed: $passed" -ForegroundColor Green
Write-Host "Failed: $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
$results | Format-Table -AutoSize

if ($failed -gt 0) {
    exit 1
}
exit 0
