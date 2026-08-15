@echo off
rem buildHomerViewBridge.cmd -- compile HomerViewBridge.exe
rem
rem Named to match the rest of the Homer Tools: buildHomerView builds the NVDA
rem add-on and its installer, and this builds the bridge the JAWS scripts use.
rem
rem Writes buildHomerViewBridge.log beside this script. Upload that log rather
rem than the console output: a redirect catches what was printed, while the log
rem also records the environment, every command run, and its exit code.
setlocal
pushd "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "buildHomerViewBridge.ps1" %*
set exitCode=%errorlevel%
popd
endlocal & exit /b %exitCode%
