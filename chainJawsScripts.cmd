@echo off
rem chainJawsScripts.cmd -- make the installed HomerView scripts reachable
rem
rem Compiling HomerView.jsb into the JAWS settings folder does not make JAWS
rem run it. This adds the two things that do: a MyExtensions.jss that uses it,
rem and keys in the user's own copies of default.jkm and msedge.jkm.
rem
rem Run it AFTER the HomerView installer has put HomerView.jsb there, and
rem restart JAWS afterwards.
rem
rem   chainJawsScripts          adds it
rem   chainJawsScripts -bUndo   puts everything back
rem
rem The log is beside this file, at chainJawsScripts.log.
setlocal
pushd "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "chainJawsScripts.ps1" %*
set exitCode=%errorlevel%
popd
endlocal & exit /b %exitCode%
