@echo off
rem probeJawsScripts.cmd
rem
rem Reports what JAWS has in every settings folder, and which key map binds
rem Control+F and to what script. It only reads: nothing is changed, created
rem or deleted.
rem
rem Writes probeJawsScripts.log beside this file. Send that log back.
setlocal
pushd "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "probeJawsScripts.ps1" %*
set exitCode=%errorlevel%
popd
endlocal & exit /b %exitCode%
