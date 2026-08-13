@echo off
rem installPandoc.cmd
rem
rem Fetches pandoc and puts it in the HomerView installation folder, which is
rem the first place HomerView looks for it.
rem
rem Not packaged with HomerView because it is about 220 megabytes: too large to
rem commit to GitHub, which refuses anything over a hundred, and a long download
rem to impose on someone who may already have it or may never open an ebook.
rem
rem Writes installPandoc.log beside itself.
setlocal
pushd "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "installPandoc.ps1" %*
set exitCode=%errorlevel%
popd
endlocal & exit /b %exitCode%
