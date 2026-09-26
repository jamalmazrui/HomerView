@echo off
rem chainJawsScripts.cmd -- make the installed HomerView scripts reachable
rem
rem Compiling HomerView.jsb into the JAWS settings folder does not make JAWS
rem run it. This writes the browser's own script file and key map, which do:
rem <browser>.jss layered over the factory set, and <browser>.jkm. Nothing
rem outside the browser is touched. Pass -sBrowserExe chrome.exe (or any
rem Chromium browser) to bind the keys there instead of in Edge; Choose
rem Browser does that for you.
rem
rem Run it AFTER the HomerView installer has put HomerView.jsb there, and
rem restart JAWS afterwards.
rem
rem   chainJawsScripts          adds it
rem   chainJawsScripts -bUndo   puts everything back
rem
rem It writes a detailed log; the path is printed when it finishes.
setlocal
pushd "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "chainJawsScripts.ps1" %*
set exitCode=%errorlevel%
popd
endlocal & exit /b %exitCode%
