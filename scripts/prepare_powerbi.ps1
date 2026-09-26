$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    throw "Create the environment first: py -3.12 -m venv .venv"
}

& $PythonExe scripts\download_uci.py
if ($LASTEXITCODE -ne 0) { throw "UCI download or integrity check failed." }

& $PythonExe -m retailscope uci --input data\raw\online_retail_II.xlsx
if ($LASTEXITCODE -ne 0) { throw "Real-data pipeline failed." }

& $PythonExe -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Unit tests failed." }

& $PythonExe scripts\validate_powerbi_contract.py --data-root outputs\real\marts
if ($LASTEXITCODE -ne 0) { throw "Power BI delivery validation failed." }

Write-Host "Power BI marts and delivery package are ready."
Write-Host "Next: open powerbi\README.md and build the report in Power BI Desktop."
