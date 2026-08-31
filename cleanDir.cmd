@echo off
rem cleanDir.cmd
rem
rem Moves everything the project does not name into notes\, deletes empty
rem files, and clears Python caches. Decides by homerPolicy.py, which reads
rem HomerView_setup.iss and RepoFiles.txt, so there is no list to maintain.
rem
rem Running it does nothing: it prints the whole plan and stops. Run it again
rem with --do-it to carry that plan out.
rem
rem     cleanDir
rem     cleanDir --do-it
rem
rem Writes cleanDir.log beside this script.
setlocal
pushd "%~dp0"
python "cleanDir.py" %*
set exitCode=%errorlevel%
popd
endlocal & exit /b %exitCode%
