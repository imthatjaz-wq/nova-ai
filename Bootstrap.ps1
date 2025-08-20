# Bootstrap.ps1 — quick setup for Nova on Windows PowerShell
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\Bootstrap.ps1

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "[Nova] Creating virtual environment (.venv)" -ForegroundColor Cyan
python -m venv .venv

$venvActivate = Join-Path $Root ".venv/ScriptS/Activate.ps1"
if (-not (Test-Path $venvActivate)) {
  $venvActivate = Join-Path $Root ".venv/Scripts/Activate.ps1"
}
. $venvActivate

Write-Host "[Nova] Upgrading pip and installing package (editable)" -ForegroundColor Cyan
python -m pip install --upgrade pip
pip install -e .

Write-Host "[Nova] Running tests" -ForegroundColor Cyan
pytest -q

Write-Host "[Nova] Done. Try 'nova --help' and 'nova version'" -ForegroundColor Green
