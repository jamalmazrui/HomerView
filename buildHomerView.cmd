@echo off
rem buildHomerView.cmd
rem Builds the add-on and the installer, in the order tagRelease expects.
rem Writes buildHomerView.log. Run this before tagRelease.
setlocal
pushd "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "buildHomerView.ps1"
set exitCode=%errorlevel%
popd
endlocal & exit /b %exitCode%
