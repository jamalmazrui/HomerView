@echo off
rem buildAddon.cmd
rem Builds the HomerView NVDA add-on and writes buildAddon.log.
setlocal
pushd "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "buildAddon.ps1"
set exitCode=%errorlevel%
popd
endlocal & exit /b %exitCode%
