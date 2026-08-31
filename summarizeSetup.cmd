@echo off
rem Shows the HomerView Results box. A wrapper so the installer never has to
rem carry PowerShell's execution-policy arguments in a quoted command line.
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0summarizeSetup.ps1" %*
endlocal
