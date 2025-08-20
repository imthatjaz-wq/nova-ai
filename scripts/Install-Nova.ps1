# Install-Nova.ps1 — simple installer for Windows
# - Creates a venv at repo root (C:\Nova\.venv)
# - Installs nova-assistant in editable mode from repo root
# - Schedules nightly consolidation at 2:00 AM (dry-run by default)
param(
  [switch]$Apply
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

Write-Host "[Nova] Creating virtual environment ($RepoRoot\.venv)" -ForegroundColor Cyan
python -m venv .venv

$venvActivate = Join-Path $RepoRoot ".venv/ScriptS/Activate.ps1"
if (-not (Test-Path $venvActivate)) {
  $venvActivate = Join-Path $RepoRoot ".venv/Scripts/Activate.ps1"
}
. $venvActivate

Write-Host "[Nova] Upgrading pip and installing package (editable)" -ForegroundColor Cyan
python -m pip install --upgrade pip
pip install -e .

Write-Host "[Nova] Scheduling nightly task (2:00 AM)" -ForegroundColor Cyan
$cmd = "python -m ui.cli jobs schedule --time 02:00" + ($(if ($Apply) {" --apply"} else {""}))
Write-Host "[Nova] Running: $cmd" -ForegroundColor DarkGray
Invoke-Expression $cmd

Write-Host "[Nova] Done. Try 'python -m ui.cli --help' and 'python -m ui.cli jobs schedule --apply' when ready." -ForegroundColor Green
