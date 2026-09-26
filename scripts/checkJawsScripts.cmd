@echo off
rem checkJawsScripts.cmd -- compile the JAWS scripts and say what went wrong
rem
rem Seconds, not minutes. This asks every JAWS compiler on the machine to read
rem jaws\HomerView.jss and reports what each one said, without building an
rem add-on, an installer, or installing anything.
rem
rem The log is beside this file, at checkJawsScripts.log.
setlocal
pushd "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "checkJawsScripts.ps1"
set exitCode=%errorlevel%
popd
endlocal & exit /b %exitCode%
