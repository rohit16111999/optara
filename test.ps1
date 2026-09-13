$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
$testScratch = Join-Path $PSScriptRoot ('.runtime/pytest-' + [Guid]::NewGuid().ToString('N'))
& .venv\Scripts\python.exe -m pytest -q "--basetemp=$testScratch"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Push-Location frontend
try {
    & node node_modules/typescript/bin/tsc --noEmit
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & node node_modules/playwright/cli.js test
    exit $LASTEXITCODE
} finally { Pop-Location }
