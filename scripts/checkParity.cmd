@echo off
rem Runs checkParity.py, which reports every NVDA command with no JAWS
rem counterpart. A wrapper so the Python path never has to be typed.
setlocal
python "%~dp0checkParity.py" %*
if errorlevel 1 echo Python could not run checkParity.py. Is Python on the path?
endlocal
