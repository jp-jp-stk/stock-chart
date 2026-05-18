# setup_scheduler.ps1
# StockChart Task Scheduler registration script
# Run with Administrator PowerShell

# -- Principal: SYSTEM account (runs regardless of login state) --
$principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

# -- Task 1: StockChart_Daily (Mon-Fri 17:15) --
$action1 = New-ScheduledTaskAction `
    -Execute "C:\Users\jnpei\Documents\stock-chart\run_daily.bat"

$trigger1 = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At "17:15"

Register-ScheduledTask `
    -TaskName  "StockChart_Daily" `
    -Action    $action1 `
    -Trigger   $trigger1 `
    -Principal $principal `
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
    -TaskName  "StockChart_Weekly" `
    -Action    $action2 `
    -Trigger   $trigger2 `
    -Principal $principal `
    -Force

Write-Host "[OK] StockChart_Weekly registered (Every Friday 17:30)"

# -- Confirm registered tasks --
Write-Host ""
Write-Host "-- Registered tasks --"
Get-ScheduledTask | Where-Object { $_.TaskName -like "StockChart*" } | `
    Select-Object TaskName, State | Format-Table -AutoSize

Write-Host "-- Logon type check --"
Get-ScheduledTask -TaskName "StockChart_Daily"  | Select-Object -ExpandProperty Principal | Select-Object UserId, LogonType
Get-ScheduledTask -TaskName "StockChart_Weekly" | Select-Object -ExpandProperty Principal | Select-Object UserId, LogonType