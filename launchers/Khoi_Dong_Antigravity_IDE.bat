@echo off
chcp 65001 >nul
title Khoi Dong Antigravity IDE (Kich hoat Auto-Submit)
cd /d "%~dp0\.."

echo ========================================================
echo   KHOI DONG ANTIGRAVITY IDE VOI AUTO-SUBMIT (PORT 9222)
echo ========================================================
echo.

:: 1. Khoi dong Auto-Submit Daemon chay ngam
wscript.exe launchers\Chay_Ngam_Auto_Submit.vbs

:: 2. Khoi dong Antigravity IDE voi cong remote debugging 9222
set "IDE_EXE=%LOCALAPPDATA%\Programs\Antigravity IDE\Antigravity IDE.exe"

if exist "%IDE_EXE%" (
    echo [OK] Dang mo Antigravity IDE voi port 9222...
    start "" "%IDE_EXE%" --remote-debugging-port=9222 %*
) else (
    echo [LOI] Khong tim thay Antigravity IDE tai: "%IDE_EXE%"
    pause
)
