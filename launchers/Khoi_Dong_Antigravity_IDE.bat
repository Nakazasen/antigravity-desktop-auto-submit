@echo off
chcp 65001 >nul
title Khoi Dong Antigravity IDE (Kich hoat Auto-Submit)
cd /d "%~dp0\.."

echo ========================================================
echo   KHOI DONG ANTIGRAVITY IDE VOI AUTO-SUBMIT (PORT 9222)
echo ========================================================
echo.

:: 1. Khoi dong Auto-Submit Daemon chay ngam neu chua chay
wscript.exe launchers\Chay_Ngam_Auto_Submit.vbs

:: 2. Kiem tra xem Antigravity IDE co dang chay hay khong
tasklist /FI "IMAGENAME eq Antigravity IDE.exe" 2>nul | find /I /N "Antigravity IDE.exe" >nul
if %errorlevel% equ 0 (
    echo [CANH BAO] Antigravity IDE hien dang chay tren may!
    echo.
    echo Luu y: Chromium chi kich hoat cong 9222 khi khoi dong IDE tu dau.
    echo Neu mo them luc nay se bi nhan doi cua so ma khong kich hoat duoc port.
    echo.
    echo Ban co muon tu dong dong toan bo IDE de khoi dong lai voi port 9222 khong?
    echo   [1] Co, dong va khoi dong lai IDE ngay bay gio (Chi mo 1 cua so duy nhat)
    echo   [2] Khong, toi se giu nguyen va dan script vao Console (Ctrl+Shift+P)
    echo.
    set /p choice="Nhap lua chon (1 hoac 2): "
    if "%choice%"=="1" (
        echo Dang tat Antigravity IDE...
        taskkill /F /IM "Antigravity IDE.exe" >nul 2>&1
        timeout /t 2 >nul
        goto :launch
    ) else (
        echo.
        echo Hay nhan Ctrl+Shift+P trong IDE > Developer: Toggle Developer Tools > Console de dan ma.
        pause
        exit /b 0
    )
)

:launch
set "IDE_EXE=%LOCALAPPDATA%\Programs\Antigravity IDE\Antigravity IDE.exe"
if exist "%IDE_EXE%" (
    echo [OK] Dang mo Antigravity IDE voi port 9222...
    start "" "%IDE_EXE%" --remote-debugging-port=9222 %*
) else (
    echo [LOI] Khong tim thay Antigravity IDE tai: "%IDE_EXE%"
    pause
)
