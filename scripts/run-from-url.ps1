#Requires -Version 5.1
<#
.SYNOPSIS
  从商品 URL 一键跑 L1 抓取 → 提示词优化 → L1-L8 管线
.EXAMPLE
  .\scripts\run-from-url.ps1 -ProductUrl "https://example.com/product/demo"
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$ProductUrl,
    [string]$Topic = "",
    [string]$Script = "",
    [string]$BaseUrl = $(if ($env:ORCHESTRATOR_URL) { $env:ORCHESTRATOR_URL } else { "http://127.0.0.1:8765" }),
    [string[]]$Layers = @("L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"),
    [switch]$SkipOptimize,
    [switch]$SkipPipeline
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "=== run-from-url ===" -ForegroundColor Cyan
Write-Host "URL: $ProductUrl"
Write-Host "API: $BaseUrl`n"

try {
    Invoke-RestMethod -Uri "$BaseUrl/health" -TimeoutSec 5 | Out-Null
}
catch {
    Write-Host "后台未启动。请先运行:" -ForegroundColor Red
    Write-Host "  cd $root" -ForegroundColor Yellow
    Write-Host "  npm run dev:api" -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/3] L1 抓取 ..." -ForegroundColor Green
$crawl = Invoke-RestMethod -Method Post -Uri "$BaseUrl/agent/crawler" -ContentType "application/json" -Body (@{
    product_url     = $ProductUrl
    competitor_urls = @()
} | ConvertTo-Json)

if (-not $crawl.ok) {
    throw "L1 crawl failed: $($crawl.error.message)"
}

$card = $crawl.data.selection_card
$title = $card.title
$category = $card.category
$pains = @($card.pain_points)

if (-not $SkipOptimize) {
    Write-Host "[2/3] 提示词优化 ..." -ForegroundColor Green
    $opt = Invoke-RestMethod -Method Post -Uri "$BaseUrl/modules/l2-content/optimize-prompts" -ContentType "application/json" -Body (@{
        product_url    = $crawl.data.crawled_url
        topic          = $Topic
        script         = $Script
        product_title  = $title
        category       = $category
        pain_points    = $pains
    } | ConvertTo-Json)

    if ($opt.ok) {
        if (-not $Topic) { $Topic = $opt.data.optimized_topic }
        if (-not $Script) { $Script = $opt.data.optimized_script }
        Write-Host "  provider: $($opt.data.provider)" -ForegroundColor DarkGray
        Write-Host "  hooks: $($opt.data.hook_suggestions -join ' | ')" -ForegroundColor DarkGray
    }
}
else {
    Write-Host "[2/3] 跳过提示词优化" -ForegroundColor DarkGray
}

if ($SkipPipeline) {
    Write-Host "`nDone (SkipPipeline). Topic/Script 已写入变量。" -ForegroundColor Cyan
    exit 0
}

Write-Host "[3/3] 运行管线 ($($Layers -join ',')) ..." -ForegroundColor Green
$pipe = Invoke-RestMethod -Method Post -Uri "$BaseUrl/pipeline/run" -ContentType "application/json" -Body (@{
    product_url = $crawl.data.crawled_url
    topic       = $Topic
    script      = $Script
    layers      = $Layers
} | ConvertTo-Json -Depth 4)

Write-Host "`n=== 结果 ===" -ForegroundColor Cyan
Write-Host "job_id: $($pipe.data.job_id)"
Write-Host "status: $($pipe.data.status) / $($pipe.data.pipeline_state)"
foreach ($lr in $pipe.data.layer_results) {
    Write-Host "  $($lr.layer_id) $($lr.status) — $($lr.message)"
}
if ($pipe.data.optimization_hints.Count -gt 0) {
    Write-Host "`nL8 建议: $($pipe.data.optimization_hints[0])"
}
