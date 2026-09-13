$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:UV_CACHE_DIR = Join-Path $PSScriptRoot '.runtime/uv-cache'
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw 'Install uv from https://docs.astral.sh/uv/getting-started/installation/ first.' }
& uv sync --frozen --python 3.12
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
$nodePath = (Get-Command node).Source
$npmCliPath = Join-Path (Split-Path $nodePath) 'node_modules/npm/bin/npm-cli.js'
if (Test-Path -LiteralPath $npmCliPath) {
    & node $npmCliPath ci --prefix frontend --cache .runtime/npm-cache --no-audit --no-fund
} else {
    & npm ci --prefix frontend --no-audit --no-fund
}
if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
Write-Host 'Optara dependencies installed. Start with .\start.ps1'
