@echo off
rem buildAll.cmd
rem Builds the add-on and the installer, in the order release expects.
rem Writes buildAll.log. Run this before release.
setlocal
pushd "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "buildAll.ps1"
set exitCode=%errorlevel%
popd
endlocal & exit /b %exitCode%
