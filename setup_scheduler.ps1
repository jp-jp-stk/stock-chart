# setup_scheduler.ps1
# StockChart Task Scheduler registration
# Automatically re-launches as Administrator if needed

# -- Auto-elevate if not running as Administrator --
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Not running as Administrator. Restarting with elevation..."
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}
Write-Host "[OK] Running as Administrator"
Write-Host ""

$SCRIPT_DIR = "C:\Users\jnpei\Documents\stock-chart"

# -- Step 1: Remove existing tasks --
Write-Host "Removing existing tasks..."
Unregister-ScheduledTask -TaskName "StockChart_Daily"  -Confirm:$false -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName "StockChart_Weekly" -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "[OK] Existing tasks removed"
Write-Host ""

# -- Principal: SYSTEM (runs regardless of logon state) --
$principal = New-ScheduledTaskPrincipal `
    -UserId    "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel  Highest

# -- Settings --
#   -AllowStartIfOnBatteries    -> DisallowStartIfOnBatteries = False (run on battery)
#   -DontStopIfGoingOnBatteries -> StopIfGoingOnBatteries     = False (no stop on battery)
#   -StartWhenAvailable         -> StartWhenAvailable = True  (run ASAP if missed)
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

# -- Task 1: StockChart_Daily (Mon-Fri 17:15) --
$action1 = New-ScheduledTaskAction `
    -Execute          "$SCRIPT_DIR\run_daily.bat" `
    -WorkingDirectory $SCRIPT_DIR

$trigger1 = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At "17:15"

Register-ScheduledTask `
    -TaskName  "StockChart_Daily" `
    -Action    $action1 `
    -Trigger   $trigger1 `
    -Principal $principal `
    -Settings  $settings `
    -Force

Write-Host "[OK] StockChart_Daily registered (Mon-Fri 17:15)"

# -- Task 2: StockChart_Weekly (Every Friday 17:30) --
$action2 = New-ScheduledTaskAction `
    -Execute          "$SCRIPT_DIR\run_weekly.bat" `
    -WorkingDirectory $SCRIPT_DIR

$trigger2 = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Friday `
    -At "17:30"

Register-ScheduledTask `
    -TaskName  "StockChart_Weekly" `
    -Action    $action2 `
    -Trigger   $trigger2 `
    -Principal $principal `
    -Settings  $settings `
    -Force

Write-Host "[OK] StockChart_Weekly registered (Every Friday 17:30)"

# -- Verification --
Write-Host ""
Write-Host "-- Registered tasks --"
Get-ScheduledTask | Where-Object { $_.TaskName -like "StockChart*" } | `
    Select-Object TaskName, State | Format-Table -AutoSize

Write-Host "-- Principal --"
Get-ScheduledTask -TaskName "StockChart_Daily" | Select-Object -ExpandProperty Principal | `
    Select-Object UserId, LogonType, RunLevel

Write-Host "-- Settings (DisallowStartIfOnBatteries=False / StopIfGoingOnBatteries=False / StartWhenAvailable=True) --"
Get-ScheduledTask -TaskName "StockChart_Daily" | Select-Object -ExpandProperty Settings | `
    Select-Object DisallowStartIfOnBatteries, StopIfGoingOnBatteries, StartWhenAvailable, ExecutionTimeLimit

Write-Host ""
Write-Host "Done. Press any key to close."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")