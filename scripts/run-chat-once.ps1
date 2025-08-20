param(
  [Parameter(Mandatory=$false)][string]$InputText = "hello"
)
$ErrorActionPreference = "Stop"
# Ensure noninteractive for deterministic behavior
$env:NOVA_NONINTERACTIVE = "1"
$env:NOVA_PERMISSION_DEFAULT = "deny"
Write-Host "[Nova] chat once: $InputText" -ForegroundColor Cyan
python -m ui.cli chat --once "$InputText"
