@echo off
chcp 65001 >nul
title Dung Antigravity Auto-Submitter
echo Dang tim va dung tien trinh Antigravity Auto-Submit Daemon...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*antigravity_auto_submit_daemon.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('[OK] Da dung tien trinh PID: ' + $_.ProcessId) }"
echo.
echo Hoan tat!
pause
