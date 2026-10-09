@echo off
chcp 65001 >nul
title Antigravity Auto-Submit
cd /d "%~dp0\.."
if not exist logs mkdir logs >nul 2>&1

:MENU
cls
echo ========================================================
echo   ANTIGRAVITY AUTO-SUBMIT (1 file duy nhat)
echo   Desktop + IDE + VS Code + tab Chrome: tu bam Submit
echo ========================================================
echo.
echo   1. Chay FULL hien log + Chrome debug (nhieu tab, khong cuop chuot)
echo   2. Chay FULL an (khong cua so, log: logs\daemon.log)
echo   3. Chi chay daemon (giu Chrome hien tai - chi tab dang mo)
echo   4. Chi mo Chrome debug (daemon dang chay roi)
echo   5. Dung HET (daemon + Chrome debug)
echo   0. Thoat
echo.
choice /C 123450 /N /M "Chon [1-5,0]: "
if %ERRORLEVEL% lss 1 goto MENU
if %ERRORLEVEL% gtr 6 goto MENU
if %ERRORLEVEL% equ 6 goto END
if %ERRORLEVEL% equ 5 goto STOPALL
if %ERRORLEVEL% equ 4 goto ONLYCHROME
if %ERRORLEVEL% equ 3 goto ONLYDAEMON
if %ERRORLEVEL% equ 2 goto FULLHID
goto FULL

:FULL
call :STOPDAEMON
call :DAEMONVIS
call :CHROME
echo.
echo [OK] Daemon + Chrome debug dang chay. Mo cac tab conv va lam viec.
pause
goto MENU

:FULLHID
call :STOPDAEMON
call :DAEMONHID
call :CHROME
echo.
echo [OK] Daemon chay an (log: logs\daemon.log). Mo cac tab conv va lam viec.
pause
goto MENU

:ONLYDAEMON
call :STOPDAEMON
choice /C HA /N /M "Hien log (H) hay chay an (A)? [H/A]: "
if %ERRORLEVEL% equ 1 call :DAEMONVIS
if %ERRORLEVEL% equ 2 call :DAEMONHID
echo.
echo [OK] Daemon dang chay.
pause
goto MENU

:ONLYCHROME
call :CHROME
pause
goto MENU

:STOPALL
call :STOPDAEMON
call :STOPCHROME
echo.
echo [OK] Da dung het.
pause
goto MENU

:STOPDAEMON
echo [*] Dung daemon cu (neu co)...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*antigravity_auto_submit_daemon*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('    Da dung daemon PID: ' + $_.ProcessId) }"
exit /b 0

:DAEMONVIS
echo [*] Khoi dong daemon (hien log)...
start "Antigravity Auto-Submit" py -3 -u scripts\antigravity_auto_submit_daemon.py --log-file logs\daemon.log
exit /b 0

:DAEMONHID
echo [*] Khoi dong daemon (an)...
powershell -NoProfile -WindowStyle Hidden -Command "Start-Process -FilePath 'py' -ArgumentList '-3','-u','scripts\antigravity_auto_submit_daemon.py','--log-file','logs\daemon.log' -WorkingDirectory '%CD%' -WindowStyle Hidden"
exit /b 0

:CHROME
tasklist /FI "IMAGENAME eq chrome.exe" 2>nul | find /I "chrome.exe" >nul
if %ERRORLEVEL% neq 0 goto CHROMELAUNCH
echo [!] Chrome dang chay. Co remote-debugging chi tac dung khi mo Chrome tu dau.
echo     (Tat dot ngot co the mat tab chua luu - can nhac truoc khi chon T.)
choice /C TG /N /M "Tat het Chrome de mo lai debug (T) hay Giu nguyen (G)? [T/G]: "
if %ERRORLEVEL% equ 2 exit /b 0
echo [*] Tat Chrome...
taskkill /F /IM chrome.exe >nul 2>&1
timeout /t 2 /nobreak >nul
:CHROMELAUNCH
set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" (
    echo [LOI] Khong tim thay chrome.exe.
    exit /b 1
)
echo [*] Mo Chrome debug port 9333...
start "" "%CHROME%" --remote-debugging-port=9333
exit /b 0

:STOPCHROME
echo [*] Dung Chrome debug (giu Chrome thuong)...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'chrome.exe' -or $_.Name -eq 'msedge.exe') -and $_.CommandLine -like '*remote-debugging-port*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('    Da dung Chrome debug PID: ' + $_.ProcessId) }"
exit /b 0

:END
