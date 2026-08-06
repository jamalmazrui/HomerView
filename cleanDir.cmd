@echo off
rem cleanDir.cmd
rem
rem Moves everything the project does not need out of C:\HomerView and into
rem C:\temp\HomerView_misc. Nothing is deleted, so a file moved by mistake can
rem be moved back.
rem
rem Writes cleanDir.log beside this script.
setlocal
pushd "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "cleanDir.ps1" %*
set exitCode=%errorlevel%
popd
endlocal & exit /b %exitCode%
