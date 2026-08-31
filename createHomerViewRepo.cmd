@echo off
rem createHomerViewRepo.cmd
rem Creates the HomerView repository, connects it to GitHub, and pushes.
rem Writes createHomerViewRepo.log. Pass -bPrivate for a private repository.
setlocal
pushd "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "createHomerViewRepo.ps1" %*
set exitCode=%errorlevel%
popd
endlocal & exit /b %exitCode%
