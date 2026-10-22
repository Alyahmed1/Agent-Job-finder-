# Run once (right-click > Run with PowerShell). Creates:
#   1) a daily 7:00 AM Windows task that updates your jobs (wakes the laptop, runs with no window)
#   2) a Desktop shortcut that opens the dashboard
# Remove the task any time with:  Unregister-ScheduledTask -TaskName WillyJobFinder-Daily -Confirm:$false
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$taskName = "WillyJobFinder-Daily"

$action   = New-ScheduledTaskAction -Execute "$root\.venv\Scripts\pythonw.exe" -Argument "scheduled_run.py" -WorkingDirectory $root
# A closed, sleeping laptop cannot run 7:00, so the task also runs when the laptop wakes, unlocks, or you log on.
# scheduled_run.py skips the work when the list was updated in the last 3 hours, so extra runs are cheap.
$daily  = New-ScheduledTaskTrigger -Daily -At "07:00"
$logon  = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$unlock = Get-CimClass -Namespace ROOT\Microsoft\Windows\TaskScheduler -ClassName MSFT_TaskSessionStateChangeTrigger |
          ForEach-Object { New-CimInstance -CimClass $_ -ClientOnly -Property @{ StateChange = 8; UserId = "$env:USERDOMAIN\$env:USERNAME" } }  # 8 = unlock
$resume = Get-CimClass -Namespace ROOT\Microsoft\Windows\TaskScheduler -ClassName MSFT_TaskEventTrigger |
          ForEach-Object { New-CimInstance -CimClass $_ -ClientOnly -Property @{
              Enabled = $true; Delay = "PT30S"
              Subscription = '<QueryList><Query Id="0" Path="System"><Select Path="System">*[System[Provider[@Name=''Microsoft-Windows-Power-Troubleshooter''] and EventID=1]]</Select></Query></QueryList>' } }
$triggers = @($daily, $logon, $unlock, $resume)
# No RunOnlyIfNetworkAvailable: right after wake the network is not up yet, and scheduled_run.py waits for it itself (up to 10 min).
# A run where every source fails exits with an error, and Windows retries it 3 times, 10 minutes apart.
$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
            -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -MultipleInstances IgnoreNew `
            -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 10)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $triggers -Settings $settings `
    -Description "Job Hunter: reads LinkedIn alerts and remote job sites at 7:00 AM and whenever the laptop wakes" -Force | Out-Null
"Task '$taskName' created. Next run: $((Get-ScheduledTaskInfo -TaskName $taskName).NextRunTime)"

$desktop = [Environment]::GetFolderPath("Desktop")
$lnk = (New-Object -ComObject WScript.Shell).CreateShortcut("$desktop\Job Finder.lnk")
$lnk.TargetPath = "$root\open_dashboard.bat"
$lnk.WorkingDirectory = $root
$lnk.WindowStyle = 7
$lnk.Save()
"Shortcut created: $desktop\Job Finder.lnk"
"Also in Windows: Power Options > Advanced > Sleep > Allow wake timers = Enable, so the laptop can wake at 7:00."
