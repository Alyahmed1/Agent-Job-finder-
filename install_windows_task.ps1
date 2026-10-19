# Run once (right-click > Run with PowerShell). Creates:
#   1) a daily 7:00 AM Windows task that updates your jobs (wakes the laptop, runs with no window)
#   2) a Desktop shortcut that opens the dashboard
# Remove the task any time with:  Unregister-ScheduledTask -TaskName WillyJobFinder-Daily -Confirm:$false
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$taskName = "WillyJobFinder-Daily"

$action   = New-ScheduledTaskAction -Execute "$root\.venv\Scripts\pythonw.exe" -Argument "scheduled_run.py" -WorkingDirectory $root
$trigger  = New-ScheduledTaskTrigger -Daily -At "07:00"
$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RunOnlyIfNetworkAvailable `
            -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "Job Finder: reads LinkedIn alerts and remote job sites at 7:00 AM" -Force | Out-Null
"Task '$taskName' created. Next run: $((Get-ScheduledTaskInfo -TaskName $taskName).NextRunTime)"

$desktop = [Environment]::GetFolderPath("Desktop")
$lnk = (New-Object -ComObject WScript.Shell).CreateShortcut("$desktop\Job Finder.lnk")
$lnk.TargetPath = "$root\open_dashboard.bat"
$lnk.WorkingDirectory = $root
$lnk.WindowStyle = 7
$lnk.Save()
"Shortcut created: $desktop\Job Finder.lnk"
"Also in Windows: Power Options > Advanced > Sleep > Allow wake timers = Enable, so the laptop can wake at 7:00."
