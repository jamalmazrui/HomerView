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
set "kitNeeded=1.43.20"
rem TRIMMED BEFORE IT IS COMPARED. FileDir's build of 25 September stopped
rem with "kit 1.40.1 is older than 1.40.1": the kit's version.txt carried a
rem trailing space, [version] would not parse "1.40.1 ", PowerShell threw, and
rem the non-zero exit was taken for "older". HomerScribe's log shows the same
rem trailing space. A comparison that cannot tell a parse failure from an old
rem kit is worse than none, so the two cases are told apart here.
powershell -NoProfile -Command "$sHave = '!homerVer!'.Trim(); $sNeed = '!kitNeeded!'.Trim(); try { if ([version]$sHave -lt [version]$sNeed) { exit 1 } else { exit 0 } } catch { Write-Host ('The kit version could not be read: ' + $sHave); exit 2 }"
if errorlevel 2 (
  echo The kit's version.txt at !homerDev! does not hold a version number.
  echo ERROR: unreadable kit version "!homerVer!">> "%log%"
  exit /b 1
)
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
rem JOINED WITH SEMICOLONS, NOT QUOTED. The first version wrapped each path
rem in quotes and passed the lot as one quoted PowerShell argument, and the
rem inner quotes did not survive the cmd-to-PowerShell boundary: the engine
rem received the paths bare, found no quotes to split on, compiled with no
rem kit sources at all, and csc answered "InixCodec does not exist". A
rem semicolon cannot appear in a Windows path, so it crosses intact.
set "homerSources=!homerDev!\CSharp\Inix.cs;!homerDev!\CSharp\Web.cs"
for %%F in ("!homerDev!\CSharp\Inix.cs" "!homerDev!\CSharp\Web.cs") do (
  if not exist %%F (
    echo The kit at !homerDev! has no %%~nxF, and HomerView.cs calls into it.
    echo ERROR: missing kit source %%F>> "%log%"
    exit /b 1
  )
)
echo Kit sources: !homerSources!>> "%log%"

rem ---- copies of the kit classes this app used to carry: gone --------
for %%F in (homer\Inix.cs homer\Web.cs homer\Keys.cs) do (
  if exist "%%F" del /q "%%F" && echo Removed the local copy %%F>> "%log%"
)
if exist "homer" rd "homer" 2>nul
rem docs\ was a second, stale copy of the documentation set. The set lives in
rem help\ now, and one copy is the right number of copies.
if exist "docs" rd /s /q "docs" && echo Removed the stale docs\ folder>> "%log%"

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
rem ONLY THE KIT TOOLS HOMERVIEW USES. The kit offers every app the same set,
rem and an app should carry what it needs rather than everything offered, as
rem an installer offers only the components that app depends on -- the spell
rem checker for EdSharp, Whisper for HomerScribe, pandoc here. Left out on
rem purpose: installScreenReaderSupport, since installJawsScripts already does
rem that job here and two tools for one job is how they drift; homerInstall,
rem the common half of install scripts HomerView does not have; and the three
rem tutorial tools, which come back the day HomerView has a tutorial.
rem THE KIT RENAMED ITS SCRIPTS ON 26 SEPTEMBER 2026: homerTidy is tidy, gitPush
rem is push, gitUnpushed is unpushed, checkHomerApp is check, tagRelease is
rem release. A NAME THE KIT DOES NOT HAVE IS SAID, NOT SKIPPED: this loop used
rem to copy "if exist", so after a rename every copy would quietly have been
rem skipped and HomerView kept its stale old-named scripts with nothing in the
rem log to say so.
for %%F in (check.cmd check.py fixEncoding.cmd fixEncoding.py push.cmd release.cmd release.ps1 tidy.cmd tidy.py unpushed.cmd unpushed.py) do (
  if exist "!homerDev!\scripts\%%F" (
    copy /y "!homerDev!\scripts\%%F" scripts\ >nul && echo Refreshed scripts\%%F>> "%log%"
  ) else (
    echo NOT IN THE KIT: scripts\%%F. The kit at !homerDev! may be older than 1.42.0.>> "%log%"
    echo The kit has no scripts\%%F. Update HomerDev to 1.42.0 or later.
  )
)
rem Retired: one tool per job, and the kit's tool is the one. And a script-set
rem leftover: HomerViewGlobal.jkm was the global key map from before the keys
rem moved into the browser's own map. Nothing reads it, but scripts\jaws\* is
rem shipped whole, so a dead file there would be installed on every machine.
if exist "scripts\jaws\HomerViewGlobal.jkm" del /q "scripts\jaws\HomerViewGlobal.jkm" && echo Removed the dead scripts\jaws\HomerViewGlobal.jkm>> "%log%"
for %%F in (buildTutorials.cmd buildTutorials.ps1 checkHomerApp.cmd checkHomerApp.py checkTutorial.cmd checkTutorial.py cleanDir.cmd cleanDir.py gitPush.cmd gitRelease.cmd gitUnpushed.cmd gitUnpushed.py homerInstall.cmd homerPolicy.py homerTidy.cmd homerTidy.py installScreenReaderSupport.cmd installTools.cmd makeTutorials.py sayTutorial.cmd sayTutorial.py tagRelease.cmd tagRelease.ps1 tidyRepo.cmd tidyRepo.py) do (
  if exist "scripts\%%F" del /q "scripts\%%F" && echo Removed retired scripts\%%F>> "%log%"
  if exist "%%F" del /q "%%F" && echo Removed retired %%F from the root>> "%log%"
)

rem ---- the JAWS set moved from jaws\ to scripts\jaws on 26 September 2026 ------
rem CARRIED ACROSS, NOT ONLY WARNED ABOUT. Unzipping adds and replaces but
rem never moves, so a delivery that moves a folder brings only the files it
rem happens to contain. On 26 September scripts\jaws held HomerView.jss alone,
rem because that was the one file a later delivery carried, while .jkm and
rem .jsd sat in the old jaws\ -- and the quality check, now reading the new
rem place, reported every command as undocumented. A file missing from the
rem new place is taken from the old; a file already there is newer and stays.
if exist "jaws" (
  if not exist "scripts\jaws" mkdir "scripts\jaws"
  for %%F in (jaws\*.*) do (
    if not exist "scripts\jaws\%%~nxF" (
      move /y "%%F" "scripts\jaws\" >nul && echo Carried jaws\%%~nxF across to scripts\jaws>> "%log%"
    )
  )
  rem AND THEN RETIRED, ONCE NOTHING IN IT IS UNIQUE. Warning about it on
  rem every build was not enough: four builds in a row said it and it stayed.
  rem Every file it still holds now has a copy in scripts\jaws, carried or
  rem newer, so moving the folder to notes\ loses nothing and can be undone.
  set "bUnique="
  for %%F in (jaws\*.*) do if not exist "scripts\jaws\%%~nxF" set "bUnique=1"
  if not defined bUnique (
    if not exist "notes" mkdir "notes"
    if exist "notes\jaws" rd /s /q "notes\jaws"
    move "jaws" "notes\jaws" >nul && echo Moved the old jaws\ to notes\jaws; scripts\jaws has every file>> "%log%"
  )
)
rem build\ held only build output, all of which exec\ now holds, so it goes
rem the same way once exec\ exists.
if exist "build" if exist "exec" (
  if not exist "notes" mkdir "notes"
  if exist "notes\build" rd /s /q "notes\build"
  move "build" "notes\build" >nul && echo Moved the old build\ to notes\build; exec\ holds the output now>> "%log%"
)

rem ---- HomerView's own tools moved into scripts\ on 26 September 2026 -------
rem Unzipping adds and replaces but never removes, so the old copies at the
rem root would stay, work, and drift -- and a person running one by habit
rem would get the old version. Each is removed only once its replacement in
rem scripts\ is actually there.
for %%N in (chainJawsScripts checkHomerViewQuality checkJawsScripts checkParity createHomerViewRepo installJawsScripts installPandoc makeDocs probeJawsScripts summarizeSetup) do (
  for %%E in (cmd ps1 py) do (
    if exist "%%N.%%E" if exist "scripts\%%N.%%E" del /q "%%N.%%E" && echo Removed the root copy %%N.%%E; it lives in scripts\ now>> "%log%"
  )
)

rem ---- the Homer encoding, before anything is compiled -----------------
rem AN EXPLICIT ARGUMENT, ALWAYS. The kit's lesson of 25 September: %* is not
rem reset by a bare call, and a tool called with none inherits the caller's.
rem On this build's first run the call below reached fixEncoding with a
rem stray "*" and cmd tried to run it as a program. Every tool ignores
rem dash-arguments it does not know, so -build is safe to pass to all.
if exist "scripts\fixEncoding.cmd" (
  call "scripts\fixEncoding.cmd" -build >> "%log%" 2>&1
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
