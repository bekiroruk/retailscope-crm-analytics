$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    throw "Once: py -3.12 -m venv .venv ; then install requirements.txt with the venv Python."
}
& $PythonExe -m retailscope all
if ($LASTEXITCODE -ne 0) { throw "Analytics pipeline failed; previous reports may be stale." }
& $PythonExe -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Verification failed." }
Start-Process (Join-Path $ProjectRoot "outputs\reports\dashboard.html")
