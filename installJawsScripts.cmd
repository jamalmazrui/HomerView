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
endlocal & exit /b %exitCode%
