$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$Host.UI.RawUI.WindowTitle = 'Optara - Secure W&B Sign-in'
$env:PYTHONUTF8 = '1'
Write-Host 'OPTARA - secure W&B sign-in' -ForegroundColor Cyan
Write-Host 'Enter your key below. Input is hidden and is never printed.'
Write-Host 'After successful verification, return to Codex and say Signed in.'
& (Join-Path $projectRoot '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'login.py')
