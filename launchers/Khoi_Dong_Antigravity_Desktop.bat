@echo off
chcp 65001 >nul
title Khoi Dong Antigravity Desktop (Kich hoat Auto-Submit)
cd /d "%~dp0\.."

echo ========================================================
echo   KHOI DONG ANTIGRAVITY DESKTOP VOI AUTO-SUBMIT (PORT 9222)
echo ========================================================
echo.

:: 1. Khoi dong Auto-Submit Daemon chay ngam
wscript.exe launchers\Chay_Ngam_Auto_Submit.vbs

:: 2. Kiem tra xem Antigravity Desktop co dang chay hay khong
tasklist /FI "IMAGENAME eq Antigravity.exe" 2>nul | find /I /N "Antigravity.exe" >nul
if %errorlevel% equ 0 (
    echo [CANH BAO] Antigravity Desktop hien dang chay tren may!
    echo.
    echo Luu y: Chromium chi kich hoat cong 9222 khi khoi dong ung dung tu dau.
    echo.
    echo Ban co muon tu dong dong de khoi dong lai voi port 9222 khong?
    echo   [1] Co, dong va khoi dong lai Antigravity ngay bay gio
    echo   [2] Khong, giu nguyen
    echo.
    set /p choice="Nhap lua chon (1 hoac 2): "
    if "%choice%"=="1" (
        echo Dang tat Antigravity Desktop...
        taskkill /F /IM "Antigravity.exe" >nul 2>&1
        timeout /t 2 >nul
        goto :launch
    ) else (
        exit /b 0
    )
)

:launch
set "AG_EXE=%LOCALAPPDATA%\Programs\Antigravity\Antigravity.exe"
if exist "%AG_EXE%" (
    echo [OK] Dang mo Antigravity Desktop voi port 9222...
    start "" "%AG_EXE%" --remote-debugging-port=9222 %*
) else (
    echo [LOI] Khong tim thay Antigravity Desktop tai: "%AG_EXE%"
    pause
)
