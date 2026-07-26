@echo off
rem clean.cmd
rem Removes build output and Python caches.
setlocal
pushd "%~dp0"
if exist "build\*.nvda-addon" del /q "build\*.nvda-addon"
if exist "buildAddon.log" del /q "buildAddon.log"
for /d /r "addon" %%D in (__pycache__) do if exist "%%D" rd /s /q "%%D"
popd
endlocal
