@echo off
chcp 65001 >nul
title Dung Antigravity Auto-Submit
echo Dung daemon...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*antigravity_auto_submit_daemon*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('[OK] Da dung daemon PID: ' + $_.ProcessId) }"
echo Dung Chrome debug (giu Chrome thuong)...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'chrome.exe' -or $_.Name -eq 'msedge.exe') -and $_.CommandLine -like '*remote-debugging-port*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('[OK] Da dung Chrome debug PID: ' + $_.ProcessId) }"
echo.
echo Hoan tat!
pause
