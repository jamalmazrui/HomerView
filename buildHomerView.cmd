@echo off
rem ===================================================================
rem buildHomerView.cmd -- build HomerView on the Homer Development Kit.
rem
rem THE KIT CONTRACT, as HomerDev_update.md states it, is carried here so
rem the PowerShell engine beneath (buildHomerView.ps1) can stay the engine:
rem
rem   1. Find the kit and state the version this app needs.
rem   2. Compile against the kit's C# sources; carry no copies.
rem   3. Refresh the kit's scripts into scripts\ on every build; retire
rem      the old ones.
rem   4. One log per session in logs\, named HomerView-build-<stamp>.log.
rem   5. Put the project's own files into the Homer encoding before the
rem      compile.
rem
rem WHY A WRAPPER RATHER THAN A REWRITE. HomerView's build does five things
rem no template build does -- it compiles the JAWS scripts against every
rem installed JAWS version, parses the PowerShell the installer will run,
rem builds a C# bridge, builds an NVDA add-on and runs twenty agreement
rem checks -- and all of that is proven code. The kit contract is about
rem where sources come from, where logs go, and which scripts the app
rem carries. Those are the wrapper's job, and the engine takes what it is
rem given.
rem
rem KIT: the shared C# modules are NOT copied into the app folder. They are
rem compiled straight out of C:\HomerDev\CSharp, so there is one copy of
rem Inix.cs on the machine and every app gets a fix the moment the kit does.
rem HomerView carried homer\Inix.cs, homer\Web.cs and homer\Keys.cs until
rem 25 September 2026; the first two had drifted from the kit's by then and
rem the third is superseded by the kit's KeyName.cs. This script deletes
rem them, and RepoFiles.txt no longer names them, so they cannot return.
rem
rem COMPILER: Roslyn is required. The kit's modules use C# beyond version
rem 5, and the pre-Roslyn csc.exe under Microsoft.NET\Framework64 stops at
rem 5 -- which is exactly why HomerView's own check 22 used to FORBID newer
rem C#: it was compiling with the old compiler. With the kit's sources on
rem the line that rule inverts: the compiler must be modern. If no Roslyn is
rem found, winget installs Build Tools; if that fails too, this says so and
rem stops, because the failure the old compiler produces is forty lines
rem about braces that never mention the language version.
rem
rem   buildHomerView.cmd          steps the version, then builds
rem   buildHomerView.cmd nobump   keeps the current number
rem ===================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

set "app=HomerView"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "sStamp=%%i"
if not exist "%~dp0logs" mkdir "%~dp0logs"
set "log=%~dp0logs\%app%-build-%sStamp%.log"
echo %app% build started %DATE% %TIME%> "%log%"
echo Script: %~f0>> "%log%"
echo Folder: %CD%>> "%log%"
echo Command line: %0 %*>> "%log%"
echo Build log: %log%

rem ---- the Homer Development Kit -------------------------------------
set "homerDev="
if defined HomerDev if exist "%HomerDev%\CSharp\Inix.cs" set "homerDev=%HomerDev%"
if not defined homerDev if exist "C:\HomerDev\CSharp\Inix.cs" set "homerDev=C:\HomerDev"
if not defined homerDev if exist "%CD%\CSharp\Inix.cs" set "homerDev=%CD%"
if not defined homerDev (
  echo %app% needs the Homer Development Kit and cannot find it.
  echo Unzip HomerDev.zip into C:\HomerDev, or set the HomerDev environment variable.
  echo ERROR: kit not found>> "%log%"
  exit /b 1
)
set "homerVer=0.0.0"
if exist "!homerDev!\version.txt" set /p homerVer=<"!homerDev!\version.txt"
set "kitNeeded=1.39.2"
powershell -NoProfile -Command "if ([version]'!homerVer!' -lt [version]'!kitNeeded!') { exit 1 } else { exit 0 }" >nul
if errorlevel 1 (
  echo %app% needs HomerDev !kitNeeded! or later, and the kit is !homerVer!.
  echo Unzip HomerDev.zip into C:\HomerDev, then build again.
  echo ERROR: kit !homerVer! is older than !kitNeeded!>> "%log%"
  exit /b 1
)
echo Kit: !homerDev! version !homerVer!
echo Kit: !homerDev! version !homerVer!>> "%log%"

rem ---- the kit sources HomerView compiles against ----------------------
rem Only the modules HomerView.cs calls. The bridge is a console program
rem with two file dialogs; it has no forms, so Lbc, Say, Elevate and Mdi
rem would be dead weight in a 190 KB binary. Add a line when a call
rem appears; the compiler names any that is missing.
set "homerSources="
set "homerSources=!homerSources! "!homerDev!\CSharp\Inix.cs""
set "homerSources=!homerSources! "!homerDev!\CSharp\Web.cs""
for %%F in ("!homerDev!\CSharp\Inix.cs" "!homerDev!\CSharp\Web.cs") do (
  if not exist %%F (
    echo The kit at !homerDev! has no %%~nxF, and HomerView.cs calls into it.
    echo ERROR: missing kit source %%F>> "%log%"
    exit /b 1
  )
)
echo Kit sources:!homerSources!>> "%log%"

rem ---- copies of the kit classes this app used to carry: gone --------
for %%F in (homer\Inix.cs homer\Web.cs homer\Keys.cs) do (
  if exist "%%F" del /q "%%F" && echo Removed the local copy %%F>> "%log%"
)
if exist "homer" rd "homer" 2>nul

rem ---- the compiler: Roslyn, or install it, or stop ----------------------
set "csc="
if exist "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe" set "csc=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe"
if not defined csc if exist "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe" set "csc=C:\Program Files\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe"
if not defined csc if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\Roslyn\csc.exe" set "csc=C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\Roslyn\csc.exe"
if not defined csc if exist "C:\Program Files (x86)\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\Roslyn\csc.exe" set "csc=C:\Program Files (x86)\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\Roslyn\csc.exe"
if not defined csc if exist "C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\Roslyn\csc.exe" set "csc=C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\Roslyn\csc.exe"
if not defined csc if exist "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\Roslyn\csc.exe" set "csc=C:\Program Files\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\Roslyn\csc.exe"
if not defined csc if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe" set "csc=C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe"
if not defined csc (
  echo No Roslyn compiler found. Installing Visual Studio Build Tools with winget...
  echo Installing Build Tools with winget>> "%log%"
  winget install --id Microsoft.VisualStudio.2022.BuildTools --exact --scope machine --accept-source-agreements --accept-package-agreements --override "--quiet --wait --add Microsoft.VisualStudio.Workload.MSBuildTools" >> "%log%" 2>&1
  echo winget exit code !errorlevel!>> "%log%"
  if exist "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe" set "csc=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe"
)
if not defined csc (
  echo No Roslyn compiler could be found or installed. The kit's classes use C#
  echo beyond version 5, and the compiler under Microsoft.NET\Framework64 stops
  echo there. Install Visual Studio Build Tools and build again.
  echo ERROR: no Roslyn csc.exe>> "%log%"
  exit /b 1
)
echo Compiler: !csc!
echo Compiler: !csc!>> "%log%"

rem ---- the kit's scripts this app carries, refreshed on every build --
if not exist "scripts" mkdir "scripts"
for %%F in (checkHomerApp.cmd checkHomerApp.py checkTutorial.cmd checkTutorial.py fixEncoding.cmd fixEncoding.py gitPush.cmd gitUnpushed.cmd gitUnpushed.py homerInstall.cmd homerTidy.cmd homerTidy.py installScreenReaderSupport.cmd makeTutorials.py buildTutorials.cmd buildTutorials.ps1 tagRelease.cmd tagRelease.ps1) do (
  if exist "!homerDev!\scripts\%%F" copy /y "!homerDev!\scripts\%%F" scripts\ >nul && echo Refreshed scripts\%%F>> "%log%"
)
rem Retired: one tool per job, and the kit's tool is the one.
for %%F in (cleanDir.cmd cleanDir.py gitRelease.cmd homerPolicy.py installTools.cmd sayTutorial.cmd sayTutorial.py tidyRepo.cmd tidyRepo.py) do (
  if exist "scripts\%%F" del /q "scripts\%%F" && echo Removed retired scripts\%%F>> "%log%"
  if exist "%%F" del /q "%%F" && echo Removed retired %%F from the root>> "%log%"
)

rem ---- the Homer encoding, before anything is compiled -----------------
if exist "scripts\fixEncoding.cmd" (
  call "scripts\fixEncoding.cmd" >> "%log%" 2>&1
  echo Encoding: fixEncoding exit code !errorlevel!>> "%log%"
)

rem ---- the engine -----------------------------------------------------
set "bump=bump"
if /i "%~1"=="nobump" set "bump=nobump"
powershell -NoProfile -ExecutionPolicy Bypass -File "buildHomerView.ps1" -pathCompiler "!csc!" -sHomerSources "!homerSources!" -pathLogFile "%log%" -sBump "%bump%"
set "exitCode=!errorlevel!"
echo Engine exit code !exitCode!>> "%log%"
if not "!exitCode!"=="0" (
  echo Build failed. The log is %log%
  exit /b !exitCode!
)
echo Build finished. The log is %log%
endlocal & exit /b 0
