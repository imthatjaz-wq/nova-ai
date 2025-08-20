$ErrorActionPreference = "Stop"
$env:NOVA_NONINTERACTIVE = "1"
$env:NOVA_PERMISSION_DEFAULT = "allow"
Write-Host "[Nova] running daily summary" -ForegroundColor Cyan
python -m ui.cli jobs daily-summary
