# =============================================================================
# Claude Code 一键安装脚本 (Windows PowerShell)
# 用法:   powershell -ExecutionPolicy Bypass -File setup-claude-code.ps1
# =============================================================================

$ErrorActionPreference = "Stop"
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "     Claude Code 一键安装脚本" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. 检查 Node.js ──────────────────────────────────────────────────────────
Write-Host "[1/5] 检查 Node.js..." -ForegroundColor Yellow
$nodeVersion = $null
try { $nodeVersion = node --version 2>$null } catch { }
if (-not $nodeVersion) {
    Write-Host "  X 未检测到 Node.js，请先安装 Node.js 18+：" -ForegroundColor Red
    Write-Host "    https://nodejs.org/en/download" -ForegroundColor White
    Write-Host "    推荐下载 LTS 版本 (.msi 安装包)" -ForegroundColor White
    Start-Process "https://nodejs.org/en/download"
    Write-Host "  安装完成后请重新运行本脚本" -ForegroundColor Yellow
    exit 1
}
Write-Host "  V Node.js $nodeVersion" -ForegroundColor Green

# ── 2. 检查 VS Code CLI ──────────────────────────────────────────────────────
Write-Host "[2/5] 检查 VS Code..." -ForegroundColor Yellow
$hasCode = $false
try { $null = Get-Command code 2>$null; $hasCode = $true } catch { }
if ($hasCode) {
    Write-Host "  V VS Code 已就绪" -ForegroundColor Green
} else {
    Write-Host "  ! 未检测到 code 命令 (扩展安装会跳过)" -ForegroundColor Yellow
    Write-Host "    如果你装了 VS Code，可以忽略此提示" -ForegroundColor White
}

# ── 3. 安装 Claude Code CLI ──────────────────────────────────────────────────
Write-Host "[3/5] 安装 Claude Code CLI..." -ForegroundColor Yellow
$claudeInstalled = $false
try { $cv = claude --version 2>$null; if ($cv) { $claudeInstalled = $true } } catch { }

if ($claudeInstalled) {
    Write-Host "  V Claude Code CLI 已安装: $cv" -ForegroundColor Green
} else {
    Write-Host "  正在下载安装 @anthropic-ai/claude-code (可能需要几分钟)..." -ForegroundColor White
    npm install -g @anthropic-ai/claude-code
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  V Claude Code CLI 安装成功!" -ForegroundColor Green
    } else {
        Write-Host "  X 安装失败，请检查网络或尝试使用代理" -ForegroundColor Red
        exit 1
    }
}

# ── 4. 配置 API Key ──────────────────────────────────────────────────────────
Write-Host "[4/5] 配置 API Key..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  请选择 API Key 配置方式:" -ForegroundColor White
Write-Host "    1 - 直接输入 Anthropic API Key (推荐)" -ForegroundColor White
Write-Host "    2 - Claude Code OAuth 登录" -ForegroundColor White
Write-Host "    3 - ccSwitch 代理模式" -ForegroundColor White
Write-Host ""

$choice = Read-Host "  请输入选项 (1/2/3, 默认1)"
if (-not $choice) { $choice = "1" }

switch ($choice) {
    "2" {
        Write-Host "  正在打开浏览器进行 OAuth 登录..." -ForegroundColor White
        claude login
    }
    "3" {
        Write-Host ""
        Write-Host "  ccSwitch = API 代理/多Key切换工具" -ForegroundColor Cyan
        Write-Host "  会把 Claude Code 的 API 请求转发到 ccSwitch 服务端" -ForegroundColor White
        Write-Host ""
        $ccsUrl = Read-Host "  请输入 ccSwitch 服务地址 (例: http://127.0.0.1:8080/v1)"
        $ccsKey = Read-Host "  请输入 ccSwitch API Key"
        if ($ccsUrl) {
            [Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL", $ccsUrl, "User")
            Write-Host "  V ANTHROPIC_BASE_URL -> $ccsUrl" -ForegroundColor Green
        }
        if ($ccsKey) {
            [Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", $ccsKey, "User")
            Write-Host "  V API Key 已设置" -ForegroundColor Green
        }
    }
    Default {
        Write-Host ""
        Write-Host "  获取 API Key: https://console.anthropic.com/" -ForegroundColor White
        Write-Host ""
        $apiKey = Read-Host "  请输入 Anthropic API Key (sk-ant-...)"
        if ($apiKey -and $apiKey.StartsWith("sk-ant-")) {
            [Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", $apiKey, "User")
            Write-Host "  V API Key 已写入用户环境变量" -ForegroundColor Green
        } else {
            Write-Host "  X Key 格式不对，跳过。请手动执行:" -ForegroundColor Red
            Write-Host '    setx ANTHROPIC_API_KEY "你的key"' -ForegroundColor White
        }
    }
}

Write-Host "  ! 提示: 配置完成后请重启终端使环境变量生效" -ForegroundColor Yellow

# ── 5. 安装 VS Code Claude Code 扩展 ────────────────────────────────────────
Write-Host "[5/5] 安装 VS Code Claude Code 扩展..." -ForegroundColor Yellow
if ($hasCode) {
    code --install-extension anthropic.claude-code 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  V VS Code 扩展安装成功!" -ForegroundColor Green
    } else {
        Write-Host "  ! 安装失败，请在 VS Code 扩展商店手动搜索 'Claude Code'" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ! 跳过 (未检测到 code 命令)" -ForegroundColor Yellow
    Write-Host "    请在 VS Code 扩展商店搜索 'Claude Code' (作者 Anthropic) 手动安装" -ForegroundColor White
}

# ── 完成 ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  全部完成!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  下一步:" -ForegroundColor Cyan
Write-Host "    1. 重启终端 (让环境变量生效)" -ForegroundColor White
Write-Host "    2. 终端输入 claude 启动 Claude Code" -ForegroundColor White
Write-Host "    3. VS Code: Ctrl+Shift+P → Claude Code: Open" -ForegroundColor White
Write-Host ""
Write-Host "  验证安装:" -ForegroundColor Cyan
Write-Host "    claude --version" -ForegroundColor White
Write-Host "    claude /help" -ForegroundColor White
Write-Host ""
