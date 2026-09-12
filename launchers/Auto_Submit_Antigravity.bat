@echo off
chcp 65001 >nul
title Antigravity Auto-Submit
cd /d "%~dp0\.."

echo ========================================================
echo   ANTIGRAVITY AUTO-SUBMIT
echo   Desktop 2.0 + IDE/extension: tu bam Submit/Allow
echo ========================================================
echo.

:: Kiem tra Python
py -3 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Python! Vui long cai dat Python 3 tren may.
    pause
    exit /b 1
)

:: Cai dat websockets neu chua co
py -3 -c "import websockets" >nul 2>&1
if %errorlevel% neq 0 (
    echo [THONG BAO] Dang cai dat thu vien 'websockets'...
    py -3 -m pip install -r requirements.txt
)

:: Chay daemon
py -3 -u scripts\antigravity_auto_submit_daemon.py
pause
