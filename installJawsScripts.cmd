@echo off
rem installJawsScripts.cmd -- install and hook up the HomerView JAWS scripts
rem
rem Normally run by HomerView_setup.exe with the JAWS box ticked. Running it by
rem hand does the same thing.
rem
rem THE LOG IS ONE FILE PER RUN, and it is not here:
rem   %LOCALAPPDATA%\HomerView\logs\HomerViewJAWS<when>.log
rem
rem The installation, the key binding, every command given afterwards and every
rem answer the browser sends all go in that one file, in the order they
rem happened. JAWSKey+L puts it on the clipboard. This wrapper used to keep a
rem second copy in C:\temp\HomerView, which meant two files saying the same
rem thing and a question every time about which one to send.
setlocal
set "logDir=%LOCALAPPDATA%\HomerView\logs"

rem -bQuiet skips the closing prompt, and nothing else. A silent installation
rem has nobody at the keyboard, so a "press any key" would wait for a key that
rem never comes and the installer -- which waits for this to finish -- would
rem hang with no window to explain itself. The flag is consumed here and not
rem passed on; the PowerShell script has no use for it.
set "bQuiet="
set "arguments=%*"
if not "%arguments%"=="%arguments:-bQuiet=%" (
    set "bQuiet=1"
    set "arguments=%arguments:-bQuiet=%"
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installJawsScripts.ps1" %arguments%
set exitCode=%errorlevel%

echo ------------------------------------------------------------
echo The log is the newest HomerViewJAWS file in:
echo   %logDir%
echo In JAWS, press JAWSKey+L to put it on the clipboard.
if not "%exitCode%"=="0" echo Something went wrong. Please send that file.
echo ------------------------------------------------------------
rem Printed WITHOUT a newline, so the caret stays on this line and JAWSKey+Up
rem Arrow reads it. Ending with echo instead put the caret on the blank line
rem below, so reading the current line said nothing and the message had to be
rem hunted for with the JAWS cursor.
if not defined bQuiet (
    <nul set /p "=Press any key to close this window. "
    pause >nul
    echo.
)
rem A ONE-LINE RESULT, FOR THE INSTALLER'S SUMMARY.
rem
rem The installer now reports what it did in a message box rather than leaving
rem a console open, and it must not have to GUESS what happened here. This file
rem says so in one line, written where the installer can read it and overwritten
rem on every run so it never describes an older attempt.
rem WRITTEN TO C:\temp, NOT BESIDE THIS SCRIPT.
rem
rem This script lives in the installation folder, under Program Files, and it
rem runs as the ORIGINAL USER rather than the elevated one -- which is right,
rem because JAWS settings belong to that user. But a standard user CANNOT WRITE
rem TO PROGRAM FILES, so the result file was never created, and the installer
rem read its absence as "the step did not run" while the scripts had in fact
rem compiled. A summary that reports a success as a failure is worse than none.
rem
rem C:\temp is writable by the user and readable by the elevated installer,
rem which is exactly what a message passed between the two of them needs.
if not exist "C:\temp" mkdir "C:\temp" 2>nul
> "C:\temp\HomerView_jaws.result" echo %exitCode%
rem THE SECOND LINE IS THE LOG FOLDER, so the installer can put its own log
rem there too. The installer runs ELEVATED and cannot resolve this user's
rem application data; THIS script runs as the user and can. Passing the path
rem up is the only way both logs end up in one place, which is what he asked
rem for: one folder to zip, not two.
>> "C:\temp\HomerView_jaws.result" echo %logDir%

rem NO LOG COPY IN C:\temp ANY MORE.
rem
rem This used to copy the log there so it could be dictated over the phone.
rem Every log now lives in one folder -- %LOCALAPPDATA%\HomerView\logs -- which
rem is the one place he asks a tester to zip, and a second copy elsewhere only
rem raises the question of which is current. The RESULT file below stays in
rem C:\temp because it is not a log: it is a message to the ELEVATED installer,
rem which cannot resolve this user's application data.
)
:copiedLog
endlocal & exit /b %exitCode%
