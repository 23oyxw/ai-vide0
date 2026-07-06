# Static export build for Gitee Pages / any static hosting
# Renames API routes temporarily, builds, and restores
$ErrorActionPreference = "Stop"

Push-Location $PSScriptRoot
try {
    Write-Host "=== Static Export for Gitee Pages ==="

    # 1. Swap config
    if (Test-Path next.config.ts) { Copy-Item next.config.ts next.config.ts.bak -Force }
    Copy-Item next.config.export.ts next.config.ts -Force

    # 2. Hide API routes (not supported in static export)
    $apiDir = "src/app/api"
    if (Test-Path $apiDir) {
        Rename-Item $apiDir "api.bak"
        Write-Host "  API routes moved aside for static build"
    }

    # 3. Build static site
    Write-Host "  Building..."
    npx next build 2>&1

    # 4. Show output
    $outDir = "out"
    if (Test-Path $outDir) {
        $files = (Get-ChildItem -Recurse -File $outDir).Count
        Write-Host "  Static export: $files files in out/"
    }

    Write-Host "=== Done ==="
} finally {
    # Restore everything
    if (Test-Path next.config.ts.bak) { Move-Item next.config.ts.bak next.config.ts -Force }
    if (Test-Path "src/app/api.bak") { Rename-Item "src/app/api.bak" "api" }
    Pop-Location
}
