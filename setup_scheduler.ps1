# setup_scheduler.ps1
# StockChart Task Scheduler registration script
# Run with Administrator PowerShell

# -- Task 1: StockChart_Daily (Mon-Fri 17:15) --
$action1 = New-ScheduledTaskAction `
    -Execute "C:\Users\jnpei\Documents\stock-chart\run_daily.bat"

$trigger1 = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At "17:15"

Register-ScheduledTask `
    -TaskName "StockChart_Daily" `
    -Action $action1 `
    -Trigger $trigger1 `
    -RunLevel Highest `
    -Force

Write-Host "[OK] StockChart_Daily registered (Mon-Fri 17:15)"

# -- Task 2: StockChart_Weekly (Every Friday 17:30) --
$action2 = New-ScheduledTaskAction `
    -Execute "C:\Users\jnpei\Documents\stock-chart\run_weekly.bat"

$trigger2 = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Friday `
    -At "17:30"

Register-ScheduledTask `
    -TaskName "StockChart_Weekly" `
    -Action $action2 `
    -Trigger $trigger2 `
    -RunLevel Highest `
    -Force

Write-Host "[OK] StockChart_Weekly registered (Every Friday 17:30)"

# -- Confirm registered tasks --
Write-Host ""
Write-Host "-- Registered tasks --"
Get-ScheduledTask | Where-Object { $_.TaskName -like "StockChart*" } | Select-Object TaskName, State