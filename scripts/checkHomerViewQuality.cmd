@echo off
rem checkHomerViewQuality.cmd -- runs checkHomerViewQuality.ps1 so the
rem execution policy parameters never have to be typed by hand.
rem
rem   checkHomerViewQuality
rem   checkHomerViewQuality -sRoot D:\SomewhereElse
rem
rem Everything after the command name is forwarded to the script.

setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0checkHomerViewQuality.ps1" %*
set iExit=%errorlevel%
echo.
if "%iExit%"=="0" (echo No problems were found.) else (echo Problems were found. See checkHomerViewQuality.log beside this script.)
<nul set /p "=Press any key to close this window."
pause >nul
exit /b %iExit%
