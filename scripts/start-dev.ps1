# 一键启动：FastAPI 后台 + Next.js 前端
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "== AI Video Orchestrator 开发环境 ==" -ForegroundColor Cyan
Write-Host "项目目录: $Root"

if (-not (Test-Path "$Root\node_modules")) {
    Write-Host "安装 npm 依赖..." -ForegroundColor Yellow
    npm install
}

function Test-Port($port) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return [bool]$conn
}

function Test-WebDashboardHealthy {
    try {
        $res = Invoke-WebRequest -Uri "http://127.0.0.1:3000/dashboard" -UseBasicParsing -TimeoutSec 8
        return $res.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Test-ApiHealthy {
    try {
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:8765/health" -TimeoutSec 3
        return $true
    } catch {
        return $false
    }
}

function Test-OrchestratorFresh {
    try {
        $spec = Invoke-RestMethod -Uri "http://127.0.0.1:8765/openapi.json" -TimeoutSec 3
        $hasOptimize = [bool]$spec.paths.'/modules/l2-content/optimize-prompts'
        $hasProductImage = [bool]$spec.paths.'/modules/l2-content/generate-product-image'
        return $hasOptimize -and $hasProductImage
    } catch {
        return $false
    }
}

function Stop-PortProcess($port) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
}

function Wait-ApiReady {
    param([int]$MaxSeconds = 20)
    for ($i = 0; $i -lt $MaxSeconds; $i++) {
        if ((Test-ApiHealthy) -and (Test-OrchestratorFresh)) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

# --- API :8765 ---
$apiOk = (Test-Port 8765) -and (Test-OrchestratorFresh)
if ((Test-Port 8765) -and -not (Test-OrchestratorFresh)) {
    Write-Host "检测到 :8765 为旧版后台（缺少 L2 新接口），正在重启..." -ForegroundColor Yellow
    Stop-PortProcess 8765
    $apiOk = $false
}

if (-not $apiOk) {
    Write-Host "启动后台 :8765 ..." -ForegroundColor Green
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "Set-Location '$Root'; uvicorn orchestrator.main:app --reload --host 127.0.0.1 --port 8765"
    )
    if (Wait-ApiReady) {
        Write-Host "后台就绪（含 L2 optimize-prompts + generate-product-image）" -ForegroundColor Green
    } else {
        Write-Host "后台启动中，若长时间未就绪请检查 python/uvicorn" -ForegroundColor Yellow
    }
} else {
    Write-Host "后台已在 :8765 运行（含 L2 新接口）" -ForegroundColor DarkGray
}

# --- Web :3000 ---
$webHealthy = (Test-Port 3000) -and (Test-WebDashboardHealthy)
if (-not (Test-Port 3000)) {
    Write-Host "启动前端 :3000 ..." -ForegroundColor Green
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "Set-Location '$Root'; npm run dev:web"
    )
    Start-Sleep -Seconds 5
} elseif (-not $webHealthy) {
    Write-Host "前端 :3000 异常（常见原因：.next 缓存与 dev 进程不同步），正在重启..." -ForegroundColor Yellow
    Stop-PortProcess 3000
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "Set-Location '$Root'; npm run dev:web:clean"
    )
    Start-Sleep -Seconds 8
} else {
    Write-Host "前端已在 :3000 运行" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "控制台:  http://localhost:3000/dashboard" -ForegroundColor Cyan
Write-Host "API 健康: http://127.0.0.1:8765/health" -ForegroundColor Cyan
Write-Host "一键出片: 粘贴链接 → 抓取 → 写脚本 → 出片 → 效果数据 / AI商品图" -ForegroundColor DarkGray
Start-Process "http://localhost:3000/dashboard"
