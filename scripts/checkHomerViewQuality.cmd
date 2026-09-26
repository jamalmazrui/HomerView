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
rem NO "Press any key" (26 September 2026). The kit's check runs this as one
rem of HomerView's acceptance checks, with its output captured, and a pause
rem there waited unseen until the release was stopped by hand.
exit /b %iExit%
