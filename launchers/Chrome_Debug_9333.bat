@echo off
chcp 65001 >nul
title Chrome Debug for Antigravity Multi-Tab
cd /d "%~dp0"

echo ========================================================
echo   CHROME + REMOTE DEBUGGING (cho Antigravity nhieu tab)
echo   De daemon tu bam Submit tren MOI tab, ke ca tab nen.
echo ========================================================
echo.

:: Neu Chrome dang chay san, co --remote-debugging-port se KHONG co tac dung.
tasklist /FI "IMAGENAME eq chrome.exe" 2>nul | find /I "chrome.exe" >nul
if %errorlevel% equ 0 (
    echo [CANH BAO] Chrome dang chay. Hay TAT HET Chrome truoc,
    echo roi chay lai file nay de bat che do remote debugging.
    pause
    exit /b 1
)

set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" (
    echo [LOI] Khong tim thay chrome.exe. Hay sua duong dan trong file nay.
    pause
    exit /b 1
)

echo [OK] Mo Chrome voi remote debugging port 9333...
echo     Sau do mo cac tab https://127.0.0.1:PORT/c/... nhu binh thuong.
start "" "%CHROME%" --remote-debugging-port=9333
