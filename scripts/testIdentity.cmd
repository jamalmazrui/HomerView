@echo off
rem testIdentity.cmd -- run the browser-identity proof. No NVDA or browser is needed.
setlocal
python "%~dp0testIdentity.py" %*
set "iExit=%errorlevel%"
if not "%iExit%"=="0" echo testIdentity failed, or Python could not run it. Is Python on the path?
endlocal & exit /b %iExit%
