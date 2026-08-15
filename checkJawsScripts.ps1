# checkJawsScripts.ps1 -- compile jaws\HomerView.jss with every JAWS on this
# machine, and say what each compiler said.
#
# This exists because of how the last several failures were found: build the
# add-on, compile the installer, run the installer, tick the JAWS box, wait for
# it to finish, then open a log in C:\temp to read a syntax error. Minutes for
# an answer the compiler gives in under a second, and the source was never
# wrong in a way any of the earlier steps could have noticed.
#
# It compiles a copy named HomerViewCheck.jss inside each JAWS settings folder,
# which is where the real installation compiles too, so Include "hjconst.jsh"
# resolves exactly as it will then. Both the copy and anything it produces are
# removed afterwards, whether it worked or not.
#
# The line numbers reported are the line numbers of jaws\HomerView.jss: the two
# paths written in are substituted within their own lines and no line is added
# or removed.
#
# THE COMPILERS DISAGREE, which is the reason every version is tried rather
# than the newest. JAWS 2026 uses a different compiler from 2024 and 2025: it
# reports what it could not parse and stops, while the older one also reports
# what it parsed and could not make sense of. A file that satisfies 2026 has
# not been shown to satisfy 2024, and on 13 August 2026 the two produced
# entirely different lists of errors for the same file.
#
# Writes checkJawsScripts.log beside itself.

$ErrorActionPreference = "Continue"

$pathRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pathLog = Join-Path $pathRoot "checkJawsScripts.log"

function writeLog {
    param([string] $sMessage)
    $sStamped = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $sMessage
    Write-Host $sStamped
    try { Add-Content -Path $pathLog -Value $sStamped -Encoding UTF8 } catch { }
}

try { Set-Content -Path $pathLog -Value "" -Encoding UTF8 } catch {
    Write-Host "The log could not be started at $pathLog : $($_.Exception.Message)"
}

writeLog "checkJawsScripts starting"
writeLog "  script:            $($MyInvocation.MyCommand.Path)"
writeLog "  PowerShell:        $($PSVersionTable.PSVersion)"
writeLog "  platform:          $([System.Environment]::OSVersion.VersionString)"
writeLog "  working directory: $(Get-Location)"
writeLog "  project root:      $pathRoot"
writeLog "  command line:      $($MyInvocation.Line.Trim())"

$pathSource = Join-Path $pathRoot "jaws\HomerView.jss"
$pathBridge = Join-Path $pathRoot "HomerView.exe"
$pathAnswer = Join-Path $env:TEMP "HomerViewAnswer.json"
writeLog "  source:            $pathSource"
writeLog "  bridge path used:  $pathBridge"
writeLog "  answer path used:  $pathAnswer"
writeLog ""

if (-not (Test-Path $pathSource)) {
    writeLog "ERROR: $pathSource is not there, so there is nothing to check."
    exit 1
}

# The same substitution the installer makes, so what is compiled here is what
# will be compiled there. A path is written into a script string, where the
# backslash is an escape, so each one is doubled.
$sSource = Get-Content $pathSource -Raw
$sSource = $sSource.Replace("@bridgePath@", $pathBridge.Replace("\", "\\"))
$sSource = $sSource.Replace("@answerPath@", $pathAnswer.Replace("\", "\\"))
$sSource = $sSource.Replace("@logFile@", (Join-Path $env:LOCALAPPDATA "HomerView\logs\HomerViewJAWScheck.log").Replace("\", "\\"))
$sSource = $sSource.Replace("@installed@", "not installed")
$sSource = $sSource.Replace("@version@", "checked, not installed")
$sSource = $sSource.Replace("@appFolder@", $pathRoot.Replace("\", "\\"))

# Anything used before it is defined, said plainly, before the compiler says it
# unrecognisably.
#
# The compiler reads the file once. A call to a function it has not reached yet
# gets a declaration invented from that call, with an int return assumed, and
# what it then reports is the assignment: "Expected sResult to be a variable of
# type int not string". That names the wrong variable, on the wrong line, for
# the wrong reason, and it cost a round trip. This says which name and which
# two lines.
$lDefined = @{}
$lSourceLines = $sSource -split "`r?`n"
for ($i = 0; $i -lt $lSourceLines.Count; $i++) {
    if ($lSourceLines[$i] -match '^(?:string |int |)(?:Function|Script)\s+(\w+)') {
        $lDefined[$Matches[1]] = $i + 1
    }
}
$iForward = 0
for ($i = 0; $i -lt $lSourceLines.Count; $i++) {
    $sLine = $lSourceLines[$i]
    if ($sLine.TrimStart().StartsWith(";")) { continue }
    if ($sLine -match '^(?:string |int |)(?:Function|Script)\s+\w') { continue }
    # A METHOD CALL IS NOT A SCRIPT CALL. "oFile.ReadAll ()" is a method on a
    # COM object and has nothing to do with the readAll Script, but \b matches
    # after the dot, so every run warned that line 339 called ReadAll before it
    # was defined. A warning that is always wrong teaches the reader to skip
    # warnings, which is how a real one gets missed.
    foreach ($match in ([regex]::Matches($sLine, '(?<![.\w])(\w+)\s*\('))) {
        $sName = $match.Groups[1].Value
        if ($lDefined.ContainsKey($sName) -and $lDefined[$sName] -gt ($i + 1)) {
            writeLog "WARNING: line $($i + 1) calls $sName, which is not defined until line $($lDefined[$sName])."
            writeLog "         The compiler will assume it returns an int and complain about"
            writeLog "         whatever the result is assigned to. Move the definition above."
            $iForward += 1
        }
    }
}
if ($iForward -eq 0) {
    writeLog "Nothing is used before it is defined."
}
writeLog ""

# THE TEN QUALITY CHECKS, run before a compiler is asked for an opinion.
#
# Each one stands for a fault that has already cost a cycle: a menu branch
# naming a script that no longer exists, a helper command with no case to
# answer it, a lone backslash that turned a JavaScript pattern into the letter
# s, a fifty thousand character command line that meant the program was never
# started at all. The compiler cannot see any of them. Every one of them
# compiles perfectly and then does nothing, or the wrong thing, in silence.
#
# It is a separate script rather than more code in this one because it also has
# to be runnable on its own, in a second, without a JAWS installation. Run from
# here it writes to the console only and every line is folded into this log, so
# a build still produces one file to read.
$iQuality = 0
$pathQuality = Join-Path $pathRoot "checkHomerViewQuality.ps1"
if (-not (Test-Path $pathQuality)) {
    writeLog "ERROR: checkHomerViewQuality.ps1 is not beside this script, so the ten"
    writeLog "       quality checks did not run. That is a missing file, not a pass."
    $iQuality = 1
} else {
    # 2>&1 so a crash in the child is captured rather than lost, and no
    # Out-Null: the whole point is that the findings reach a reader.
    $lQuality = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $pathQuality `
        -sRoot $pathRoot -bChild 2>&1
    $iQuality = $LASTEXITCODE
    $iQualityLines = 0
    foreach ($oLine in $lQuality) {
        $sLine = ([string] $oLine).TrimEnd()
        if ($sLine -eq "") { continue }
        writeLog "  $sLine"
        $iQualityLines = $iQualityLines + 1
    }
    # AN EXIT CODE ON ITS OWN IS NOT A RESULT. If the child said nothing it did
    # not run, whatever it returned, and that is a failure rather than a pass.
    if ($iQualityLines -eq 0) {
        writeLog "ERROR: the quality checks produced no output at all, so they did not run."
        $iQuality = 1
    } elseif ($iQuality -ne 0) {
        writeLog "The quality checks found problems. They are listed immediately above."
    }
}
writeLog ""

$pathJawsRoot = Join-Path $env:APPDATA "Freedom Scientific\JAWS"
if (-not (Test-Path $pathJawsRoot)) {
    writeLog "JAWS is not installed for this user, so the scripts cannot be compiled here."
    writeLog "That is not a failure. The NVDA add-on does not need them."
    exit $iQuality
}

$lVersions = @(Get-ChildItem -Path $pathJawsRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^\d{4}(\.\d+)?$' })
if ($lVersions.Count -eq 0) {
    writeLog "No JAWS version folders were found under $pathJawsRoot."
    exit $iQuality
}
writeLog "JAWS versions found: $(($lVersions | ForEach-Object { $_.Name }) -join ', ')"
writeLog ""

$iGood = 0
$iBad = 0

foreach ($folderVersion in $lVersions) {
    $sVersion = $folderVersion.Name
    writeLog "JAWS $sVersion"

    $lCandidates = @(
        (Join-Path ${env:ProgramFiles} "Freedom Scientific\JAWS\$sVersion\scompile.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Freedom Scientific\JAWS\$sVersion\scompile.exe")
    )
    $sCompiler = $lCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $sCompiler) {
        writeLog "  scompile.exe for JAWS $sVersion was not found; looked in:"
        foreach ($s in $lCandidates) { writeLog "    $s" }
        writeLog "  Skipped. This version cannot say whether the source is good."
        writeLog ""
        continue
    }

    # A three letter code is a language folder. Notifications and VoiceProfiles
    # sit beside them and are not script folders.
    $lSettings = @(Get-ChildItem -Path (Join-Path $folderVersion.FullName "Settings") -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^[A-Za-z]{3}$' })
    if ($lSettings.Count -eq 0) {
        writeLog "  no settings folder, so skipping this version"
        writeLog ""
        continue
    }

    foreach ($folderLanguage in $lSettings) {
        $pathTarget = $folderLanguage.FullName
        $pathCheckJss = Join-Path $pathTarget "HomerViewCheck.jss"
        $pathCheckJsb = Join-Path $pathTarget "HomerViewCheck.jsb"
        writeLog "  settings: $pathTarget"
        try {
            Set-Content -Path $pathCheckJss -Value $sSource -Encoding UTF8 -NoNewline
            if (Test-Path $pathCheckJsb) { Remove-Item $pathCheckJsb -Force }
            writeLog "    compiling with $sCompiler"
            $sOutput = & $sCompiler $pathCheckJss 2>&1 | Out-String
            $iExit = $LASTEXITCODE
            foreach ($sLine in ($sOutput -split "`n")) {
                if ($sLine.Trim()) { writeLog "      $($sLine.Trim())" }
            }

            # What the compiler SAID, and then what it left behind. scompile
            # writes a small stub even when it has rejected the source, so a
            # file existing proves nothing: an earlier installer reported a
            # successful compile for every one of nine folders while the
            # source had a syntax error in it.
            $bGood = $true
            if ($sOutput -match '(?m)^.*\bError:') {
                writeLog "    ERROR: the compiler rejected the source. The lines above say where,"
                writeLog "           by line number in jaws\HomerView.jss."
                $bGood = $false
            }
            if ($bGood) {
                if (Test-Path $pathCheckJsb) {
                    $iSize = (Get-Item $pathCheckJsb).Length
                    if ($iSize -lt 500) {
                        writeLog "    ERROR: the compiled file is only $iSize bytes, which is a stub"
                        writeLog "           rather than a build."
                        $bGood = $false
                    } else {
                        writeLog "    compiled cleanly, $iSize bytes"
                    }
                } else {
                    writeLog "    ERROR: nothing was compiled, exit code $iExit"
                    $bGood = $false
                }
            }
            if ($bGood) { $iGood += 1 } else { $iBad += 1 }
        } catch {
            writeLog "    ERROR: the check itself failed: $($_.Exception.Message)"
            $iBad += 1
        } finally {
            # Nothing of the check is left in the user's own settings folder,
            # whichever way it went.
            foreach ($pathLeftover in @($pathCheckJss, $pathCheckJsb)) {
                if (Test-Path $pathLeftover) {
                    Remove-Item $pathLeftover -Force -ErrorAction SilentlyContinue
                }
            }
        }
    }
    writeLog ""
}

writeLog "Finished. $iGood compiled, $iBad with a problem, quality checks $(if ($iQuality -eq 0) { 'clean' } else { 'FAILED' })."
if ($iQuality -ne 0) {
    writeLog "The source compiles or not on its own account, but the quality checks"
    writeLog "failed, so this is not a build to hand over. Their findings are above."
    exit 1
}
if ($iBad -gt 0) {
    writeLog "Fix jaws\HomerView.jss and run this again. It takes about a second per"
    writeLog "version, so there is no reason to reach for the installer to find out."
    exit 1
}
if ($iGood -eq 0) {
    writeLog "Nothing was compiled, so nothing has been shown either way."
    exit $iQuality
}
writeLog "The JAWS scripts compile everywhere they were tried."
exit 0
