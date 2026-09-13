$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
& .venv\Scripts\python.exe -m marimo run experiment_lab/optara_lab.py --host 127.0.0.1 --port 2718 --headless --no-sandbox
