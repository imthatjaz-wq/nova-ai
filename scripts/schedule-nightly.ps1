# Schedules a nightly Windows Task to run Nova's nightly consolidation at 2:00 AM
param(
    [string]$TaskName = "NovaNightly",
    [string]$WorkingDir = "$PSScriptRoot\..",
    [string]$Python = "python",
    [string]$Args = "-m ui.cli jobs nightly"
)

$Action = New-ScheduledTaskAction -Execute $Python -Argument $Args -WorkingDirectory $WorkingDir
$Trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM
$Settings = New-ScheduledTaskSettingsSet -Compatibility Win8 -StartWhenAvailable

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false | Out-Null
}

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Run Nova nightly job" | Out-Null
Write-Host "Scheduled task '$TaskName' created to run daily at 2:00 AM."
