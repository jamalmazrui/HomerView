# installJawsScripts.ps1 -- put the HomerView scripts into every JAWS version
#
# The approach is the one that has proved reliable: find every JAWS settings
# folder on the machine, copy the scripts into each, and compile them with THAT
# version's own compiler. A .jsb built by one year's compiler is not reliably
# loaded by another year's JAWS, so compiling once and copying the binary
# everywhere does not work.
#
# Run as the ordinary user, never elevated. JAWS keeps its settings under the
# user's roaming application data, so an elevated run would write to the
# administrator's profile and the user would see nothing.
#
# Writes to one timestamped log in %LOCALAPPDATA%\HomerView\logs.

param(
    [switch] $bUninstall,
    # WHERE TO LOG, when the usual place is about to be deleted.
    #
    # The uninstaller passes a path in the temporary folder, because the folder
    # this normally logs into is removed moments later -- so a removal that went
    # wrong would erase the only record of how. Empty means the usual place.
    [string] $pathLogFile = "",
    [string] $sHomerVersion = "unknown"
)

$ErrorActionPreference = "Continue"

$pathRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
# ONE runtime log, shared with the bridge and the scripts.
#
# There used to be four: two in C:\temp\HomerView from this script and its
# wrapper, one beside chainJawsScripts, and the bridge's own. Four files to
# find and send, three of which said the same thing about the same run. This
# one holds the installation, the key binding, every command a user gives and
# every answer the browser sends, in the order they happened, and JAWSKey+L
# puts it on the clipboard.
#
# It cannot go beside this script, because after installation that is inside
# Program Files, which is read only without elevation while this runs as the
# ordinary user.
$pathLogFolder = Join-Path $env:LOCALAPPDATA "HomerView\logs"
try { New-Item -ItemType Directory -Path $pathLogFolder -Force | Out-Null } catch { }
# One file per run, named for the screen reader it is about and stamped with
# when it started, so a log can be told apart from the one before it without
# opening either. The scripts and the bridge append to the newest one, so an
# installation and the commands that follow it stay together in one file.
$pathLog = Join-Path $pathLogFolder ("HomerViewJAWS{0:yyyyMMdd-HHmmss}.log" -f (Get-Date))
if ($pathLogFile -ne "") { $pathLog = $pathLogFile }

function writeLog {
    param([string] $sMessage)
    $sStamped = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $sMessage
    Write-Host $sStamped
    try { Add-Content -Path $pathLog -Value $sStamped -Encoding UTF8 } catch { }
}

try {
    Add-Content -Path $pathLog -Value "" -Encoding UTF8
} catch {
    # A script that cannot write its log should still do its job. Losing the
    # record is a nuisance; losing the installation is a failure.
    Write-Host "The log could not be started at $pathLog : $($_.Exception.Message)"
}
# --- The parts ---------------------------------------------------------------
#
# Defined before the body that calls them. PowerShell runs a script from the
# top, so a function called before its definition is not yet known: the first
# version of this file had them at the bottom, which would have failed on the
# first folder it found.

function compileScript {
    param([string] $sVersion, [string] $pathSettings)

    # THAT version's compiler, not any compiler. A .jsb built by one year's
    # scompile is not reliably loaded by another year's JAWS, which is why the
    # scripts are compiled in place for each version rather than built once.
    $lCandidates = @(
        (Join-Path ${env:ProgramFiles} "Freedom Scientific\JAWS\$sVersion\scompile.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Freedom Scientific\JAWS\$sVersion\scompile.exe")
    )
    $sCompiler = $lCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $sCompiler) {
        # NOT A FAILURE. A SETTINGS FOLDER OUTLIVES THE JAWS THAT MADE IT.
        #
        # A tester had folders for JAWS 2019 through 2023 left behind by
        # upgrades, with no scompile.exe because those versions are long gone.
        # Every one was counted as a problem, so the installer exited 1 and the
        # summary box said "JAWS scripts: FAILED" -- while all three INSTALLED
        # versions had compiled cleanly and all 41 keys had bound. A report that
        # calls a success a failure is worse than no report, and it cost that
        # tester an evening.
        #
        # chainJawsScripts had this right all along: it SKIPS such folders and
        # says "3 folders done, 6 skipped, 0 with a problem".
        writeLog "    JAWS $sVersion is not installed here (no scompile.exe), so it is skipped."
        writeLog "      The files are in place if that version is ever reinstalled."
        return "skipped"
    }

    $pathJss = Join-Path $pathSettings "HomerView.jss"
    writeLog "    compiling with $sCompiler"
    $sOutput = & $sCompiler $pathJss 2>&1 | Out-String
    $iExit = $LASTEXITCODE
    foreach ($sLine in ($sOutput -split "`n")) {
        if ($sLine.Trim()) { writeLog "      $($sLine.Trim())" }
    }

    # The compiler's exit code is not always the whole story, so the file it
    # should have produced is what decides.
    # What the compiler SAID, not merely whether a file appeared. scompile
    # writes a small stub even when it has rejected the source, so the file
    # existing proves nothing: an earlier version reported a successful compile
    # for every one of nine folders while the source had a syntax error in it.
    if ($sOutput -match '(?m)^.*\bError:') {
        writeLog "    ERROR: the compiler rejected the source. The lines above say where."
        return $false
    }
    $pathJsb = Join-Path $pathSettings "HomerView.jsb"
    if (Test-Path $pathJsb) {
        $iSize = (Get-Item $pathJsb).Length
        if ($iSize -lt 500) {
            writeLog "    ERROR: HomerView.jsb is only $iSize bytes, which is a stub rather"
            writeLog "           than a build. The compiler did not accept the source."
            return $false
        }
        writeLog "    compiled HomerView.jsb ($iSize bytes)"
        return $true
    }
    writeLog "    ERROR: no HomerView.jsb was produced, exit code $iExit"
    return $false
}

function installPrebuiltJsb {
    param([string] $pathSettings)

    # WHEN THE COMPILER REFUSES, USE THE BUILD WE ALREADY HAVE.
    #
    # This is not the preferred path and it is here because of a real one: a
    # tester's scompile rejects this source on JAWS 2024, 2025 AND 2026 where
    # every version on the developer's machine accepts it. Whatever differs is
    # in his JAWS installation, and chasing it has already cost him more of that
    # tester's time than the feature is worth.
    #
    # IT IS NOT RECKLESS. Freedom Scientific's own note on JAWS 13 says scripts
    # compiled with JAWS 13 "will not be backwardly compatible with earlier
    # versions" -- which says plainly that a .jsb runs on the version that built
    # it and on LATER ones. The shipped build comes from the OLDEST JAWS present
    # when the installer was made, so it is the most portable one available, and
    # checkJawsScripts reports in the build log whether every version produced a
    # byte identical file.
    #
    # IT IS ALSO SAID OUT LOUD. A script set that came from someone else's
    # compiler is a thing the reader should know about, not a silent substitute.
    $pathPrebuilt = Join-Path $PSScriptRoot "jaws\HomerView.jsb"
    if (-not (Test-Path $pathPrebuilt)) {
        writeLog "    no prebuilt HomerView.jsb is available, so this version has none"
        return $false
    }
    try {
        $pathJsb = Join-Path $pathSettings "HomerView.jsb"
        Copy-Item $pathPrebuilt $pathJsb -Force
        $iSize = (Get-Item $pathJsb).Length
        writeLog "    the compiler refused, so the PREBUILT HomerView.jsb was installed"
        writeLog "      ($iSize bytes, built when this installer was made)"
        writeLog "      The scripts will work; only this machine's compiler is unhappy."
        return $true
    } catch {
        writeLog "    the prebuilt HomerView.jsb could not be copied: $($_.Exception.Message)"
        return $false
    }
}

function addGlobalBinding {
    param([string] $pathSettings)

    # Deliberately does nothing, and the reason is worth keeping.
    #
    # An earlier version merged one line into the user's default.jkm, to give
    # the launch command a key that works everywhere. That was wrong. A copy of
    # default.jkm in the user settings folder can shadow the factory one rather
    # than adding to it, and the cost of getting that wrong is every built-in
    # JAWS binding the user has.
    #
    # No feature of HomerView is worth that risk. The launch command is reached
    # instead from the Start Menu shortcut, or from a key the user assigns in
    # JAWS Keyboard Manager, which is the supported way and leaves their own
    # settings theirs.
    writeLog "    default.jkm is left alone here; run chainJawsScripts to bind the keys"
}

function removeGlobalBinding {
    param([string] $pathSettings)
    # Nothing to undo, since nothing is done to default.jkm. Kept so an
    # installation made by an earlier version is cleaned up on removal.
    $pathDefault = Join-Path $pathSettings "default.jkm"
    if (-not (Test-Path $pathDefault)) { return }
    $sContent = Get-Content $pathDefault -Raw
    $sNew = $sContent -replace '(?m)^; Added by HomerView[^
]*
?
', ''
    $sNew = $sNew -replace '(?m)^Alt\+JAWSKey\+H=launchHomerView
?
', ''
    if ($sNew -ne $sContent) {
        Set-Content -Path $pathDefault -Value $sNew -Encoding UTF8
        writeLog "    removed a launch key left by an earlier version"
    }
}


# The parameter is what the installer passes; version.txt is what is sitting in
# the folder. Either alone has failed, so both are tried — and this has to
# happen BEFORE the header, which is where it went wrong the first time: the
# fallback was written thirty lines too late and the header said "unknown"
# while the scripts, substituted afterwards, had the version all along.
if ($sHomerVersion -eq "unknown") {
    $pathVersion = Join-Path $pathRoot "version.txt"
    if (Test-Path $pathVersion) {
        try { $sHomerVersion = (Get-Content $pathVersion -Raw).Trim() } catch { }
    }
}

# THE HEADER. Everything needed to know what this log is about, and nothing
# about who owns the machine beyond what the paths already give away. No user
# name, no machine name, no network, no serial numbers: a log is going to be
# sent to somebody, and it should carry only what helps them.
writeLog "=========================================================="
writeLog "HomerView $sHomerVersion for JAWS"
writeLog "  started:      $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
writeLog "  Windows:      $([System.Environment]::OSVersion.VersionString)"
writeLog "  64 bit:       $([System.Environment]::Is64BitOperatingSystem)"
writeLog "  PowerShell:   $($PSVersionTable.PSVersion)"
writeLog "  language:     $((Get-Culture).Name)"
$sJawsList = ""
try {
    $sJawsList = (Get-ChildItem -Path (Join-Path $env:APPDATA "Freedom Scientific\JAWS") -Directory -ErrorAction Stop |
        Where-Object { $_.Name -match '^\d{4}' } | ForEach-Object { $_.Name }) -join ", "
} catch { }
writeLog "  JAWS:         $(if ($sJawsList) { $sJawsList } else { 'none found' })"
$sEdgeVersion = "not found"
foreach ($sEdge in @(
    (Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe"),
    (Join-Path ${env:ProgramFiles} "Microsoft\Edge\Application\msedge.exe"))) {
    if (Test-Path $sEdge) {
        $sEdgeVersion = (Get-Item $sEdge).VersionInfo.ProductVersion
        break
    }
}
writeLog "  Edge:         $sEdgeVersion"
writeLog "=========================================================="
writeLog ""
writeLog "installJawsScripts starting"
writeLog "  script:            $($MyInvocation.MyCommand.Path)"
writeLog "  PowerShell:        $($PSVersionTable.PSVersion)"
writeLog "  platform:          $([System.Environment]::OSVersion.VersionString)"
writeLog "  running as:        $env:USERNAME"
writeLog "  roaming data:      $env:APPDATA"
writeLog "  uninstalling:      $bUninstall"

# The two paths that are written into the script source as it is copied.
#
# The scripts used to work these out for themselves, with built-in functions
# whose names and return types were guessed rather than read, and that guessing
# is what the compiler rejected release after release. This side knows both
# answers already: the bridge was just put beside this file, and this runs as
# the user whose temporary folder the answer goes in.
$pathBridge = Join-Path $pathRoot "HomerView.exe"
$pathAnswer = Join-Path $env:TEMP "HomerViewAnswer.json"
$pathJawsLogFolder = Join-Path $env:LOCALAPPDATA "HomerView\logs"
# Written into the scripts so the menu can say which copy JAWS has loaded.
# Twice now a fault has been reported against scripts JAWS had not reloaded,
# and there was no way to tell from inside JAWS which build was running.
$sInstalled = Get-Date -Format "HH:mm d MMM"
writeLog "  bridge:            $pathBridge"
writeLog "  answer file:       $pathAnswer"
writeLog "  log file:          $pathLog"
writeLog "  install stamp:     $sInstalled"
if (-not (Test-Path $pathBridge)) {
    writeLog "  WARNING: the bridge is not there. The scripts will install and compile,"
    writeLog "           but every command will report that it cannot be found."
}
writeLog ""

# Every JAWS settings folder. The year folders under the user's roaming data
# are what JAWS actually loads from, and there is one per version installed.
$pathJawsRoot = Join-Path $env:APPDATA "Freedom Scientific\JAWS"
if (-not (Test-Path $pathJawsRoot)) {
    writeLog "JAWS is not installed for this user, so there is nothing to do."
    writeLog "That is not a failure. HomerView works with NVDA on its own."
    exit 0
}

$lVersions = @(Get-ChildItem -Path $pathJawsRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^\d{4}(\.\d+)?$' })
if ($lVersions.Count -eq 0) {
    writeLog "No JAWS version folders were found under $pathJawsRoot."
    exit 0
}
writeLog "JAWS versions found: $(($lVersions | ForEach-Object { $_.Name }) -join ', ')"
writeLog ""

$lScripts = @("HomerView.jss", "HomerView.jkm", "HomerView.jsd")
$iDone = 0
$iFailed = 0
$iSkipped = 0

foreach ($folderVersion in $lVersions) {
    $sVersion = $folderVersion.Name
    writeLog "JAWS $sVersion"

    # The language folder. Almost always enu, but take whatever is there so a
    # user running JAWS in another language is not silently skipped.
    # Only the LANGUAGE folders. A JAWS settings folder also holds
        # Notifications and VoiceProfiles, which are not script folders, and an
        # earlier version copied the scripts into those too and compiled them
        # there. It put files where nothing would ever read them, and tripled
        # both the work and the log.
        #
        # A language folder is named with a three letter code: enu, fra, deu.
        $lSettings = @(Get-ChildItem -Path (Join-Path $folderVersion.FullName "Settings") -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^[A-Za-z]{3}$' })
    if ($lSettings.Count -eq 0) {
        writeLog "  no settings folder, so skipping this version"
        continue
    }

    foreach ($folderLanguage in $lSettings) {
        $pathTarget = $folderLanguage.FullName
        writeLog "  settings: $pathTarget"

        if ($bUninstall) {
            foreach ($sName in ($lScripts + @("HomerView.jsb"))) {
                $pathFile = Join-Path $pathTarget $sName
                if (Test-Path $pathFile) {
                    Remove-Item $pathFile -Force -ErrorAction SilentlyContinue
                    writeLog "    removed $sName"
                }
            }
            removeGlobalBinding $pathTarget
            $iDone += 1
            continue
        }

        # The script files.
        $bCopied = $true
        foreach ($sName in $lScripts) {
            $pathSource = Join-Path $pathRoot "jaws\$sName"
            if (-not (Test-Path $pathSource)) {
                writeLog "    ERROR: $sName is missing from the installation"
                $bCopied = $false
                continue
            }
            try {
                if ($sName -eq "HomerView.jss") {
                    # Written rather than copied. A backslash in a script string
                    # is an escape, so each one in a Windows path is doubled on
                    # the way in; a path written in raw would turn C:\temp into a
                    # tab and the compiler would not say so.
                    $sSource = Get-Content $pathSource -Raw
                    $sSource = $sSource.Replace("@bridgePath@", $pathBridge.Replace("\", "\\"))
                    $sSource = $sSource.Replace("@answerPath@", $pathAnswer.Replace("\", "\\"))
                    $sSource = $sSource.Replace("@logFile@", $pathLog.Replace("\", "\\"))
                    $sSource = $sSource.Replace("@appFolder@", $pathRoot.Replace("\", "\\"))
                    $sSource = $sSource.Replace("@installed@", $sInstalled)
                    $sSource = $sSource.Replace("@version@", $sHomerVersion)
                    if ($sSource.Contains("@bridgePath@") -or $sSource.Contains("@answerPath@") -or $sSource.Contains("@logFile@") -or $sSource.Contains("@appFolder@") -or $sSource.Contains("@installed@") -or $sSource.Contains("@version@")) {
                        writeLog "    ERROR: a path could not be written into $sName"
                        $bCopied = $false
                        continue
                    }
                    Set-Content -Path (Join-Path $pathTarget $sName) -Value $sSource -Encoding UTF8 -NoNewline
                    writeLog "    wrote $sName, with the bridge and answer paths in it"
                } else {
                    Copy-Item $pathSource (Join-Path $pathTarget $sName) -Force
                    writeLog "    copied $sName"
                }
            } catch {
                writeLog "    ERROR copying $sName : $($_.Exception.Message)"
                $bCopied = $false
            }
        }
        if (-not $bCopied) { $iFailed += 1; continue }

        addGlobalBinding $pathTarget
        $vCompiled = compileScript $sVersion $pathTarget
        if ($vCompiled -eq "skipped") {
            $iSkipped += 1
        } elseif ($vCompiled) {
            $iDone += 1
        } elseif (installPrebuiltJsb $pathTarget) {
            $iDone += 1
        } else {
            $iFailed += 1
        }
    }
    writeLog ""
}

writeLog "Finished. $iDone settings folders done, $iSkipped skipped, $iFailed with a problem."
if ($iFailed -gt 0) {
    writeLog "HomerView still works with NVDA. The JAWS scripts are the part that failed."
}
# The keys, done here rather than by hand.
#
# Compiling the scripts into the settings folder does not make JAWS load them:
# it loads the file named after the running program, and nothing is called
# HomerView.exe. chainJawsScripts writes the MyExtensions file that pulls ours
# in and puts the keys in the user's own copy of default.jkm. It used to be a
# separate thing to remember to run. Anything a person has to remember to run
# after an installer is a step that will one day be skipped.
$pathChain = Join-Path $pathRoot "chainJawsScripts.ps1"
if (-not (Test-Path $pathChain)) {
    writeLog "WARNING: chainJawsScripts.ps1 is not installed, so the keys were NOT bound."
    writeLog "         The scripts are compiled but JAWS will not load them."
} else {
    writeLog ""
    if ($bUninstall) {
        writeLog "Unbinding the keys and unhooking the scripts"
    } else {
        writeLog "Binding the keys and hooking the scripts into JAWS"
    }
    $lChainArguments = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $pathChain, "-pathLogFile", $pathLog)
    if ($bUninstall) { $lChainArguments += "-bUndo" }
    # Its output is normally NOT folded in: it writes to this same file itself,
    # and folding would print every line of it twice.
    #
    # BUT THE OUTPUT IS KEPT NOW RATHER THAN DISCARDED, because "$null = &" threw
    # away the one thing worth having. When the child failed BEFORE it could
    # open the log -- a missing file, a parse error in its own source -- this
    # log said "the keys could not be bound. The lines above say why" WITH
    # NOTHING ABOVE IT. The sentence pointed at an empty space.
    #
    # So it is captured, and folded in ONLY when the child failed and wrote
    # nothing of its own.
    $iBefore = 0
    if (Test-Path $pathLog) { $iBefore = (Get-Content $pathLog).Count }
    $ErrorActionPreference = "Continue"
    $sChainOutput = & powershell @lChainArguments 2>&1 | Out-String
    $iChain = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    if ($iChain -ne 0) {
        $iAfter = 0
        if (Test-Path $pathLog) { $iAfter = (Get-Content $pathLog).Count }
        if ($iAfter -gt $iBefore) {
            writeLog "ERROR: the keys could not be bound. The lines above say why."
        } else {
            writeLog "ERROR: the keys could not be bound, and chainJawsScripts wrote"
            writeLog "       nothing of its own, so it failed before it could start."
            writeLog "       It said:"
            foreach ($sLine in ($sChainOutput -split "`n")) {
                if ($sLine.Trim()) { writeLog "         $($sLine.Trim())" }
            }
            if (-not $sChainOutput.Trim()) {
                writeLog "         (nothing at all -- check that $pathChain exists)"
            }
        }
        $iFailed += 1
    }
}

writeLog ""

# TELL JAWS TO RELOAD, SO NOBODY HAS TO RESTART IT.
#
# JAWS loads its compiled scripts once, at startup. Writing a newer .jsb into
# the settings folder changes nothing until it looks again, which is why every
# release so far has ended in "restart JAWS" -- and why a fault was once chased
# for an hour against scripts that were still the previous build.
#
# ReloadAllConfigs is Freedom Scientific's own answer, and its documentation
# describes this exact case: adjust a script, recompile with the command line
# compiler, and see the effect without restarting. It is a script function, so
# it has to be called from inside JAWS -- freedomsci.jawsapi is the COM object
# that lets a program outside ask JAWS to run one.
#
# RunFunction returns true when the call was SCHEDULED, not when it finished,
# so its answer is worth logging and worth nothing else. If a command
# afterwards behaves like an older build, restarting JAWS is still the certain
# cure, and Alt+Shift+H says which build is actually loaded.
# ON REMOVAL TOO, AND THERE FOR A BETTER REASON.
#
# On installation a reload saves a restart. On REMOVAL it prevents a fault:
# JAWS still holds the old HomerView.jsb in memory and the old keys bound, so
# every HomerView key goes on half-working against a program whose files have
# gone, until something makes JAWS look again. Asking for the reload is the
# difference between an uninstall that finishes now and one that finishes
# whenever the user next restarts JAWS.
$bReloaded = $false
try {
    $oJaws = New-Object -ComObject "freedomsci.jawsapi" -ErrorAction Stop
    $bScheduled = $oJaws.RunFunction("ReloadAllConfigs")
    writeLog "Asked JAWS to reload its configurations: scheduled = $bScheduled"
    $bReloaded = $true
    [void] [System.Runtime.InteropServices.Marshal]::ReleaseComObject($oJaws)
} catch {
    writeLog "JAWS could not be asked to reload: $($_.Exception.Message)"
}
if ($bReloaded -and $bUninstall) {
    writeLog "JAWS has been asked to reload, so the removed keys stop responding now."
} elseif ($bReloaded) {
    writeLog "No restart should be needed. Press Alt+Shift+H to see which build is loaded;"
    writeLog "if it is not this one, restart JAWS."
} elseif ($bUninstall) {
    writeLog "RESTART JAWS so it forgets the scripts that have just been removed."
} else {
    writeLog "RESTART JAWS for this to take effect."
}
writeLog "The log is at $pathLog"
# The exit code says what happened, because until now it did not. This script
# reported every failure in its log and then exited nought, so the window that
# ran it congratulated the user either way and nothing downstream could tell
# the difference. That is the same fault as counting a compile that failed.
if ($iFailed -gt 0) { exit 1 }
exit 0


