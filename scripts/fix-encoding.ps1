#Requires -Version 5.1
<#
.SYNOPSIS
  Convert UTF-16 source files to UTF-8 (no BOM) to fix garbled Chinese in UI/API.
#>
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$utf8 = New-Object System.Text.UTF8Encoding $false
$fixed = 0

Get-ChildItem -Path $root -Recurse -Include *.ts,*.tsx,*.py,*.md -File |
  Where-Object {
    $_.FullName -notmatch 'node_modules|\.next|\.venv|dist'
  } |
  ForEach-Object {
    $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
    if ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) {
      $text = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::Unicode)
      [System.IO.File]::WriteAllText($_.FullName, $text, $utf8)
      Write-Host "Fixed UTF-16 -> UTF-8: $($_.FullName.Replace($root + '\', ''))" -ForegroundColor Green
      $script:fixed++
    }
  }

Write-Host "`nDone. Fixed $fixed file(s)." -ForegroundColor Cyan
