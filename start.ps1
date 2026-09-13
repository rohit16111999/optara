param([switch]$Production)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
if ($Production) { & node (Join-Path $PSScriptRoot 'scripts/dev.mjs') --production }
else { & node (Join-Path $PSScriptRoot 'scripts/dev.mjs') }
exit $LASTEXITCODE
