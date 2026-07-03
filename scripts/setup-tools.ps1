#Requires -Version 5.1
<#
.SYNOPSIS
  Verify toolchain paths for ai-video-orchestrator.
#>
param(
    [switch]$FixPath
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "=== AI Video Orchestrator - Tool Check ===" -ForegroundColor Cyan

$checks = @(
    @{ Name = "ffmpeg"; Path = "C:\Users\oyxw\bin\ffmpeg\ffmpeg.exe"; Cmd = "ffmpeg" },
    @{ Name = "git"; Path = $null; Cmd = "git" },
    @{ Name = "gh"; Path = $null; Cmd = "gh" },
    @{ Name = "python"; Path = $null; Cmd = "python" },
    @{ Name = "C4D Commandline"; Path = "C:\BKC4D\Commandline.exe"; Cmd = $null },
    @{ Name = "C4D c4dpy"; Path = "C:\BKC4D\c4dpy.exe"; Cmd = $null },
    @{ Name = "video-factory"; Path = "C:\Users\oyxw\Projects\video-factory\run.py"; Cmd = $null },
    @{ Name = "ai-koubo"; Path = "C:\Users\oyxw\Projects\ai-koubo-platform"; Cmd = $null },
    @{ Name = "openclaw"; Path = $null; Cmd = "openclaw" }
)

$allOk = $true
foreach ($c in $checks) {
    $ok = $false
    if ($c.Path -and (Test-Path $c.Path)) { $ok = $true }
    elseif ($c.Cmd) {
        $found = Get-Command $c.Cmd -ErrorAction SilentlyContinue
        if ($found) { $ok = $true; $c.Path = $found.Source }
    }
    $icon = if ($ok) { "[OK]" } else { "[--]" ; $allOk = $false }
    $color = if ($ok) { "Green" } else { "Yellow" }
    Write-Host "$icon $($c.Name): $($c.Path)" -ForegroundColor $color
}

# Load .env if present
$envFile = Join-Path $root ".env"
if (Test-Path $envFile) {
    Write-Host "`n.env found at $envFile" -ForegroundColor Gray
} else {
    Write-Host "`nTip: copy .env.example to .env" -ForegroundColor Yellow
}

# API key check (presence only, never print values)
$keys = @("DEEPSEEK_API_KEY", "OPENAI_API_KEY")
Write-Host "`nAPI Keys (presence only):" -ForegroundColor Cyan
foreach ($k in $keys) {
    $val = [Environment]::GetEnvironmentVariable($k, "User")
    if (-not $val) { $val = [Environment]::GetEnvironmentVariable($k, "Machine") }
    $present = [bool]$val
    Write-Host "  $k : $(if ($present) { 'set' } else { 'missing' })" -ForegroundColor $(if ($present) { "Green" } else { "Yellow" })
}

if ($allOk) {
    Write-Host "`nAll critical tools found." -ForegroundColor Green
} else {
    Write-Host "`nSome tools missing - orchestrator will skip unavailable adapters." -ForegroundColor Yellow
}
