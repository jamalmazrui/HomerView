# buildHomerView.ps1
# Builds everything a release needs, in the order tagRelease expects:
# the add-on package, then the installer whose version resource tagRelease reads.
# Writes buildHomerView.log beside itself.

$ErrorActionPreference = "Stop"

$pathRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pathLog = Join-Path $pathRoot "buildHomerView.log"

function writeLog {
    param([string] $sMessage)
    $sStamped = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $sMessage
    Write-Host $sStamped
    Add-Content -Path $pathLog -Value $sStamped -Encoding UTF8
}

Set-Content -Path $pathLog -Value "" -Encoding UTF8
function checkSetupScript {
    # Everything Inno Setup will reject, found before Inno Setup sees it. Its
    # own report is a line number and four words, which is enough to find the
    # line and not enough to explain it.
    $pathSetup = Join-Path $pathRoot "HomerView_setup.iss"
    if (Test-Path $pathSetup) {
        $lLines = Get-Content $pathSetup
        $bInSetup = $false
        $dSeen = @{}
        $iProblems = 0
        foreach ($sLine in $lLines) {
            $sTrimmed = $sLine.Trim()
            if ($sTrimmed -match '^\[(\w+)\]') {
                $bInSetup = ($Matches[1] -eq "Setup")
                continue
            }
            if (-not $bInSetup) { continue }
            if ($sTrimmed.StartsWith(";") -or $sTrimmed.StartsWith("#") -or -not $sTrimmed.Contains("=")) { continue }
            $sName = $sTrimmed.Split("=")[0].Trim()
            if ($dSeen.ContainsKey($sName)) {
                writeLog "ERROR: [Setup] directive $sName is specified more than once. Inno Setup will refuse to compile."
                $iProblems += 1
            }
            $dSeen[$sName] = $true
        }
        foreach ($sLine in $lLines) {
            if ($sLine -match 'Source:\s*"([^"]+)"' -and $sLine -notmatch 'skipifsourcedoesntexist') {
                $sSource = $Matches[1]
                if ($sSource -notmatch '\*') {
                    $sResolved = $sSource -replace '\{#AddonFile\}', 'HomerView.nvda-addon'
                    if (-not (Test-Path $sResolved)) {
                        writeLog "ERROR: the setup script references $sResolved, which does not exist."
                        $iProblems += 1
                    }
                }
            }
        }
        # A setup script that has lost a section still compiles, and produces an
        # installer that installs nothing. That happened once, from an edit that
        # matched the word Run inside a comment instead of the section header, and
        # it was found by a user rather than by the build.
        foreach ($sSection in @("[Setup]", "[Files]", "[Icons]", "[Run]", "[Code]")) {
            if (-not ($lLines | Where-Object { $_.Trim() -eq $sSection })) {
                writeLog "ERROR: the setup script has no $sSection section."
                $iProblems += 1
            }
        }
        $iSources = ($lLines | Where-Object { $_.TrimStart().StartsWith("Source:") }).Count
        if ($iSources -lt 5) {
            writeLog "ERROR: the setup script lists only $iSources files to install, which is too"
            writeLog "       few to be right. A section has probably been lost."
            $iProblems += 1
        }
    
        # A flag valid in one section is not valid in every section. Inno Setup
    # rejects an unknown flag rather than ignoring it, and runasoriginaluser in
    # [UninstallRun] is what stopped a build: it is a [Run] flag, and the two
    # sections look similar enough that the mistake is easy.
    $dSectionFlags = @{
        "Run" = @("postinstall","skipifsilent","runascurrentuser","runasoriginaluser",
            "nowait","shellexec","waituntilterminated","waituntilidle","runhidden",
            "runminimized","runmaximized","skipifdoesntexist","unchecked","hidewizard",
            "64bit","dontlogparameters")
        "UninstallRun" = @("runhidden","runminimized","runmaximized","shellexec",
            "skipifdoesntexist","waituntilterminated","waituntilidle","64bit",
            "dontlogparameters","hidewizard")
    }
    $sSection = ""
    $iLine = 0
    foreach ($sLine in $lLines) {
        $iLine += 1
        $sTrimmed = $sLine.Trim()
        if ($sTrimmed -match '^\[(\w+)\]') { $sSection = $Matches[1] }
        if (-not $dSectionFlags.ContainsKey($sSection)) { continue }
        if ($sTrimmed -notmatch 'Flags:\s*([^;\\]+)') { continue }
        foreach ($sFlag in ($Matches[1] -split '\s+')) {
            if (-not $sFlag) { continue }
            if ($dSectionFlags[$sSection] -notcontains $sFlag.ToLower()) {
                writeLog "ERROR: line $iLine uses the flag $sFlag, which is not valid in"
                writeLog "       the [$sSection] section. Inno Setup rejects an unknown flag"
                writeLog "       rather than ignoring it."
                $iProblems += 1
            }
        }
    }

    # A line beginning with an opening bracket is read as a section header, and
        # a line beginning with a hash as a preprocessor directive, in both cases
        # before Pascal is compiled and regardless of any comment it sits inside.
        $lValidSections = @("[setup]","[types]","[components]","[tasks]","[dirs]","[files]",
            "[icons]","[ini]","[installdelete]","[languages]","[messages]","[custommessages]",
            "[langoptions]","[registry]","[run]","[uninstalldelete]","[uninstallrun]","[code]")
        $iLine = 0
        foreach ($sLine in $lLines) {
            $iLine += 1
            $sTrimmed = $sLine.Trim()
            if ($sTrimmed.StartsWith("[") -and (-not ($lValidSections -contains $sTrimmed.ToLower()))) {
                writeLog "ERROR: line $iLine begins with an opening bracket but is not a section"
                writeLog "       header, so Inno Setup will reject it: $sTrimmed"
                writeLog "       Start the line with a word instead, even inside a comment."
                $iProblems += 1
            }
        }
    
        # Inno Setup's preprocessor runs over the whole file before Pascal sees it,
        # and reads any line whose first non-blank character is a hash as a
        # directive. So #13#10 at the start of a line inside [Code] fails to
        # compile with nothing but a line number to go on. Catching it here says
        # what is wrong.
        $lDirectives = @("#define","#include","#if","#ifdef","#ifndef","#else",
            "#elif","#endif","#emit","#expr","#error","#pragma","#sub","#endsub",
            "#for","#dim","#undef","#file","#insert","#append")
        $iLine = 0
        foreach ($sLine in $lLines) {
            $iLine += 1
            $sTrimmed = $sLine.Trim()
            if (-not $sTrimmed.StartsWith("#")) { continue }
            $bKnown = $false
            foreach ($sDirective in $lDirectives) {
                if ($sTrimmed.ToLower().StartsWith($sDirective)) { $bKnown = $true; break }
            }
            if (-not $bKnown) {
                writeLog "ERROR: line $iLine begins with a leading hash that is not a preprocessor"
                writeLog "       directive: $sTrimmed"
                writeLog "       Inside [Code], put the value in a variable or start the line with"
                writeLog "       something else. Chr(13) + Chr(10) avoids the problem entirely."
                $iProblems += 1
            }
        }
    
        if ($iProblems -gt 0) {
            writeLog "The setup script has $iProblems problem(s). Fix them before compiling."
            exit 1
        }
        writeLog "The setup script checks out."
    }
}

function buildBridge {
    # The command line utility the JAWS scripts use.
    #
    # JAWS scripting cannot open a WebSocket, which is where every Chrome
    # DevTools command that reads or acts on a page travels. This program holds
    # that side: a script runs it, it asks the browser, and it writes the answer
    # to a file the script reads.
    #
    # Compiled with csc.exe from the .NET Framework, which is on every Windows
    # machine already, so this needs no Visual Studio and no NuGet.
    $pathSource = Join-Path $pathRoot "HomerView.cs"
    $pathBridge = Join-Path $pathRoot "HomerView.exe"
    if (-not (Test-Path $pathSource)) {
        writeLog "HomerView.cs is not here, so the JAWS bridge is skipped."
        writeLog "The NVDA add-on does not need it; only the JAWS scripts do."
        return
    }

    $pathCompiler = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
    if (-not (Test-Path $pathCompiler)) {
        writeLog "ERROR: the .NET Framework compiler was not found at $pathCompiler."
        writeLog "       That file ships with Windows, so something is unusual here."
        exit 1
    }

    if (Test-Path $pathBridge) {
        Remove-Item $pathBridge -Force
        writeLog "Removed the previous $pathBridge"
    }
    writeLog "Compiling with $pathCompiler"
    # System.Windows.Forms for the clipboard, which is the only way to put a
    # file on it in the format Explorer and Outlook understand. No window is
    # ever shown; the assembly is referenced for one class.
    #
    # System.Runtime.Serialization for JsonReaderWriterFactory, which reads the
    # browser's JSON and presents it as XML. That is what lets the JAWS side
    # use the XML functions it has instead of the JSON functions it does not,
    # and it means no JSON parser is written by hand on either side.
    #
    # System.Xml for XmlDocument and XPath. csc reads csc.rsp and references a
    # list of assemblies by default, and System.Xml is very likely on it -- but
    # "very likely" is how this project has lost afternoons before, a duplicate
    # reference costs nothing, and being wrong costs a build.
    #
    # ALL THREE SHIP WITH .NET FRAMEWORK. Nothing is downloaded, and no third
    # party JSON library is needed: JsonReaderWriterFactory has been in
    # System.Runtime.Serialization since .NET 3.5.
    #
    # System.IO.Compression for ZipArchive, which is how the .xlsx is
    # written. A spreadsheet is a zip of XML parts, so writing one needs no
    # library -- the same approach exportReport.py takes on the NVDA side.
    # See the note at the installer step: 2>&1 with ErrorActionPreference
    # "Stop" turns a native program's first stderr line into a TERMINATING
    # error, killing the script before it can log why. csc writes its errors
    # to stdout so this has not bitten here, but the trap is identical.
    $ErrorActionPreference = "Continue"
    $sOutput = & $pathCompiler /nologo /target:exe /platform:x64 `
        /reference:System.Windows.Forms.dll `
        /reference:System.Runtime.Serialization.dll `
        /reference:System.Xml.dll `
        /reference:System.IO.Compression.dll `
        "/out:$pathBridge" $pathSource 2>&1 | Out-String
    $iExit = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    foreach ($sLine in ($sOutput -split "`n")) {
        if ($sLine.Trim()) { writeLog "    $($sLine.Trim())" }
    }
    if ($iExit -ne 0 -or -not (Test-Path $pathBridge)) {
        writeLog "ERROR: the bridge did not build, exit code $iExit."
        exit 1
    }
    writeLog "Built HomerView.exe, $([math]::Round((Get-Item $pathBridge).Length / 1KB)) KB."

    # It must at least run. A program that compiles and will not start is worth
    # finding here rather than from a JAWS script that got no answer.
    $pathProbe = Join-Path $env:TEMP "HomerViewProbe.txt"
    if (Test-Path $pathProbe) { Remove-Item $pathProbe -Force }
    & $pathBridge "tabs" $pathProbe 2>&1 | Out-Null
    if (Test-Path $pathProbe) {
        writeLog "It runs and answers. (An error about connecting is expected here:"
        writeLog "HomerView's browser is not running during a build.)"
        Remove-Item $pathProbe -Force
    } else {
        writeLog "WARNING: the bridge wrote no file, which it should do even on failure."
    }
}


function buildAddon {
    # Packaging the add-on, folded in from what used to be a second script.
    #
    # One script, one log. The split meant two logs for one build, and the
    # reason for a failure could be in whichever of them the reader had not
    # been asked for. Nothing about packaging a zip needed its own program.
    #
    # The add-on always has the same name, HomerView.nvda-addon, so the setup
    # script never has to be edited when the version changes. One file, not
    # two: a copy named for the version was written here as well, and two
    # identical files with different names in one folder invites the wrong one
    # being picked up. The version is in the manifest, which is what NVDA reads.
    $pathAddon = Join-Path $pathRoot "addon"
    $pathBuild = Join-Path $pathRoot "build"
    # What went in, gathered rather than announced line by line.
    $script:lIncluded = New-Object System.Collections.ArrayList

    $pathManifest = Join-Path $pathAddon "manifest.ini"
    $sVersion = ""
    foreach ($sLine in Get-Content $pathManifest) {
        if ($sLine -match '^\s*version\s*=\s*"([^"]+)"') {
            $sVersion = $Matches[1]
        }
    }
    if (-not $sVersion) {
        writeLog "ERROR: no version was found in manifest.ini"
        exit 1
    }
    writeLog "Version $sVersion"

    # Written out so the installed program can say what it is.
    #
    # Nothing that reaches the installation folder carried the version, so the
    # JAWS log's header said "HomerView unknown". The installer passes it as a
    # parameter too, and this is the belt to that pair of braces: a parameter
    # can go astray between four programs, a file in the folder cannot.
    Set-Content -Path (Join-Path $pathRoot "version.txt") -Value $sVersion -Encoding ASCII -NoNewline
    writeLog "Wrote version.txt"

    if (-not (Test-Path $pathBuild)) {
        New-Item -ItemType Directory -Path $pathBuild | Out-Null
        writeLog "Created $pathBuild"
    }

    $pathOutput = Join-Path $pathBuild "HomerView.nvda-addon"
    if (Test-Path $pathOutput) {
        Remove-Item $pathOutput -Force
        writeLog "Removed the previous $pathOutput"

        # Stale documents. Unzipping a new version over an old folder adds and
        # replaces but never removes, so a document that has been renamed leaves
        # its old name behind and that old name is then packaged. HomerView.htm
        # survived the rename to HomerView.htm exactly this way.
        $pathDocs = Join-Path $pathAddon "doc\en"
        if (Test-Path $pathDocs) {
            $lExpected = @("Announce.htm", "HomerView.htm", "Developer.htm", "History.htm",
                "ReadMe.htm", "Hotkeys.htm", "readme.html")
            foreach ($fileDoc in (Get-ChildItem -Path $pathDocs -File)) {
                if ($lExpected -notcontains $fileDoc.Name) {
                    Remove-Item $fileDoc.FullName -Force
                    writeLog "Removed the stale document $($fileDoc.Name), which the project no longer generates"
                }
            }
        }
    }
    # Any versioned copy an earlier build left behind, so the folder holds one file.
    foreach ($pathOld in (Get-ChildItem $pathBuild -Filter "HomerView-*.nvda-addon" -ErrorAction SilentlyContinue)) {
        Remove-Item $pathOld.FullName -Force
        writeLog "Removed the leftover $($pathOld.Name)"
    }

    foreach ($pathCache in (Get-ChildItem -Path $pathAddon -Recurse -Directory -Filter "__pycache__")) {
        Remove-Item $pathCache.FullName -Recurse -Force
        writeLog "Removed $($pathCache.FullName)"
    }

    foreach ($pathFile in (Get-ChildItem -Path $pathAddon -Recurse -File)) {
        $null = $lIncluded.Add($pathFile.FullName.Substring($pathAddon.Length + 1))
    }

    Compress-Archive -Path (Join-Path $pathAddon "*") -DestinationPath "$pathOutput.zip" -Force
    Move-Item "$pathOutput.zip" $pathOutput -Force
    $iModules = @($lIncluded | Where-Object { $_ -like "*.py" }).Count
    $iDocuments = @($lIncluded | Where-Object { $_ -like "doc\*" }).Count
    writeLog "Included $($lIncluded.Count) files: $iModules Python modules, $iDocuments documents, and the manifest."
    writeLog "Wrote $pathOutput"



}

writeLog "buildHomerView starting"

# The environment, recorded before anything can fail. A log that says only what
# went wrong, and not what it went wrong on, sends the reader back to ask.
writeLog "  script:            $($MyInvocation.MyCommand.Path)"
writeLog "  PowerShell:        $($PSVersionTable.PSVersion)"
writeLog "  platform:          $([System.Environment]::OSVersion.VersionString)"
writeLog "  working directory: $(Get-Location)"
writeLog "  project root:      $pathRoot"
writeLog "  command line:      $($MyInvocation.Line.Trim())"
$commandPython = Get-Command python -ErrorAction SilentlyContinue
if ($commandPython) {
    writeLog "  Python:            $(& python --version 2>&1)"
}
writeLog ""

# The checks run FIRST. An earlier version ran them after the installer was
# compiled, which the log made plain: buildHomerView finished, and then it
# announced it was checking the setup script. A check nobody can act on is not
# a check, and the whole point of these is to stop a bad script reaching Inno
# Setup, which reports a line number and four words.
writeLog "Step 1 of 5: checking the setup script and the sources"
writeLog "Checking HomerView_setup.iss"
checkSetupScript

# A second copy of a shipped file is a copy that will diverge, and this one
# already had. The installer ships jaws\*, so the copies of HomerView.jss,
# HomerView.jkm, HomerView.jsd and HomerViewGlobal.jkm that sat in the project
# root were read by nobody, and the root HomerView.jss had been left behind at
# an older and broken revision. Anyone opening the one in the root would have
# been reading a file that no build and no installer had touched for days.
foreach ($sStray in @("HomerView.jss", "HomerView.jkm", "HomerView.jsd", "HomerViewGlobal.jkm")) {
    $pathStray = Join-Path $pathRoot $sStray
    if (Test-Path $pathStray) {
        writeLog "WARNING: $sStray is in the project root as well as in jaws\, and only the"
        writeLog "         one in jaws\ is built and shipped. Delete the root copy."
    }
}
writeLog ""

# The JAWS scripts, before anything is built rather than after everything is
# installed.
#
# Every JSL failure so far has been found by building an add-on, compiling an
# installer, running it, ticking the JAWS box and then opening a log in
# C:\temp: minutes for an answer the compiler gives in under a second. The
# check runs here, on the same footing as the setup script check, and for the
# same reason.
#
# It does not stop the build. The NVDA add-on is unaffected by the state of the
# JAWS scripts, and an installer worth testing should still be produced. What
# it does is make the build finish with a failure, so that tagRelease does not
# run on a release whose JAWS half does not compile.
writeLog "Step 2 of 5: checking that the JAWS scripts compile"
$script:bJawsFailed = $false
$pathCheck = Join-Path $pathRoot "checkJawsScripts.ps1"
if (-not (Test-Path $pathCheck)) {
    writeLog "WARNING: checkJawsScripts.ps1 is not here, so the JAWS scripts were not checked."
} else {
    # A child process, and its output captured into this log. The one log a
    # person is asked for has to hold the reason, not a note that the reason
    # is in another file.
    $ErrorActionPreference = "Continue"
    $sOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File $pathCheck 2>&1 | Out-String
    $iCheck = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    foreach ($sLine in ($sOutput -split "`n")) {
        $sTrimmed = $sLine.Trim()
        if (-not $sTrimmed) { continue }
        # The child stamps its own lines and this log stamps them again, so
        # every folded line read "2026-08-14 00:39:18  2026-08-14 00:39:18 ...".
        # Twice the date and none of the meaning, on every line of a log that
        # is listened to rather than glanced at.
        # The trailing whitespace is optional. It was not, and the child's
        # BLANK lines arrive as a bare timestamp with nothing after it for the
        # pattern to match, so half of them survived and the log still read
        # like a stutter.
        $sTrimmed = ($sTrimmed -replace '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s*', '').Trim()
        if (-not $sTrimmed) { continue }
        writeLog "    $sTrimmed"
    }
    # THE CHILD'S OWN LOG FILE, FOLDED IN TOO -- OR ACCOUNTED FOR.
    #
    # He asked for ONE file to upload after a build. Its console output is
    # already above, and comparing the two files line for line showed every
    # line of checkJawsScripts.log ALREADY PRESENT HERE. So there is nothing to
    # copy, and copying it anyway would double a 200-line log for no gain.
    #
    # What was missing is SAYING SO. A second log file sitting beside this one
    # invites the question of what is in it, and the answer belongs in the file
    # he actually sends.
    $pathCheckLog = Join-Path $pathRoot "checkJawsScripts.log"
    if (Test-Path $pathCheckLog) {
        $lCheckLog = @(Get-Content $pathCheckLog | Where-Object { $_.Trim() })
        $lHere = @(Get-Content $pathLog | Where-Object { $_.Trim() }) |
            ForEach-Object { ($_ -replace '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s*', '').Trim() }
        $lExtra = @($lCheckLog | ForEach-Object {
                ($_ -replace '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s*', '').Trim()
            } | Where-Object { $_ -and ($lHere -notcontains $_) })
        if ($lExtra.Count -eq 0) {
            writeLog "    checkJawsScripts.log holds nothing that is not already above."
        } else {
            writeLog "    checkJawsScripts.log also held $($lExtra.Count) line(s), folded in here:"
            foreach ($sLine in $lExtra) { writeLog "      $sLine" }
        }
    }
    if ($iCheck -ne 0) {
        writeLog "ERROR: the JAWS scripts did not compile. The build carries on, because the"
        writeLog "       NVDA add-on does not depend on them, but it will finish as a failure."
        $script:bJawsFailed = $true
    }
}
writeLog ""

writeLog "Step 3 of 5: building the bridge for JAWS"
buildBridge
writeLog ""

writeLog "Step 4 of 5: building the add-on"
buildAddon

# Even on success, record what the add-on build produced, so this log alone
# answers the ordinary questions: how many files, and how big.
$pathBuilt = Join-Path $pathRoot "build\HomerView.nvda-addon"
if (Test-Path $pathBuilt) {
    $nAddonSize = [math]::Round((Get-Item $pathBuilt).Length / 1KB)
    writeLog "The add-on is $nAddonSize KB."
}

# Inno Setup's compiler is not on the path by default, so look where its own
# installer puts it rather than asking the user to add it.
$pathCompiler = ""
foreach ($sCandidate in @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 5\ISCC.exe")) {
    if (Test-Path $sCandidate) { $pathCompiler = $sCandidate; break }
}
if (-not $pathCompiler) {
    $command = Get-Command "iscc.exe" -ErrorAction SilentlyContinue
    if ($command) { $pathCompiler = $command.Source }
}
if (-not $pathCompiler) {
    writeLog "ERROR: the Inno Setup compiler was not found."
    writeLog "       Install it from https://jrsoftware.org/isdl.php, then run this again."
    exit 1
}
writeLog "Inno Setup compiler: $pathCompiler"

writeLog "Step 5 of 5: compiling the installer"
# Captured, not just run. The first version let Inno Setup print to the console
# and logged four words when it failed, so the one log a person uploads said
# that something went wrong and nothing about what. Inno Setup names the line
# and the reason; that belongs in the log.
# 2>&1 IS A TRAP WHEN ErrorActionPreference IS "Stop", AND IT COST A BUILD.
#
# Redirecting a native program's stderr into the pipeline turns each of its
# error lines into a PowerShell ErrorRecord. With Stop in force, the FIRST such
# line TERMINATES THE SCRIPT -- so when Inno Setup reported a fault, this line
# threw before the next line could log anything, and the log simply STOPPED
# after "Step 5 of 5" with no reason given. The capture written to explain a
# failure was itself the reason nothing was explained.
#
# Stopping for the duration of the call is enough: the exit code is checked
# immediately below, so a failure is still a failure -- it is now a REPORTED
# one.
$sOutput = ""
try {
    $ErrorActionPreference = "Continue"
    $sOutput = & $pathCompiler (Join-Path $pathRoot "HomerView_setup.iss") 2>&1 | Out-String
    $iExit = $LASTEXITCODE
} finally {
    $ErrorActionPreference = "Stop"
}
if ($iExit -ne 0) {
    writeLog "ERROR: the installer did not compile, exit code $iExit."
    writeLog "Inno Setup said:"
    foreach ($sLine in ($sOutput -split "`n")) {
        if ($sLine.Trim()) { writeLog "    $($sLine.Trim())" }
    }
    exit 1
}
# On success only the last few lines matter; the rest is a list of files.
$lLines = @($sOutput -split "`n" | Where-Object { $_.Trim() })
foreach ($sLine in ($lLines | Select-Object -Last 3)) {
    writeLog "    $($sLine.Trim())"
}

$pathInstaller = Join-Path $pathRoot "HomerView_setup.exe"
if (-not (Test-Path $pathInstaller)) {
    writeLog "ERROR: HomerView_setup.exe was not produced. Check OutputDir in the setup script."
    exit 1
}
# Trimmed. A version resource is a fixed-width field, so it arrives padded,
# and the log read "version 1.41.0              , 2.7 MB".
$sVersion = ((Get-Item $pathInstaller).VersionInfo.FileVersion).Trim()
writeLog "Built HomerView_setup.exe, version $sVersion, $([math]::Round((Get-Item $pathInstaller).Length/1MB,1)) MB"
# What was built is checked against what was meant to be built. The add-on and
# the installer carry versions from two different files, and a release where
# they disagree is one nobody notices until a user reports the wrong number.
$sManifestVersion = ""
$pathManifest = Join-Path $pathRoot "addon\manifest.ini"
if (Test-Path $pathManifest) {
    $matchVersion = Select-String -Path $pathManifest -Pattern 'version\s*=\s*"([^"]+)"'
    if ($matchVersion) { $sManifestVersion = $matchVersion.Matches[0].Groups[1].Value }
}
if ($sManifestVersion -and ($sManifestVersion -ne $sVersion)) {
    writeLog "ERROR: the add-on says $sManifestVersion and the installer says $sVersion."
    writeLog "       They come from addon\manifest.ini and HomerView_setup.iss, and both"
    writeLog "       need changing for a release."
    exit 1
}
writeLog "The add-on and the installer both say $sVersion."

# Every module the add-on imports must be inside it. A module left out builds
# cleanly and fails on the user's machine at the moment they press the key.
$pathBuiltAddon = Join-Path $pathRoot "build\HomerView.nvda-addon"
if (-not (Test-Path $pathBuiltAddon)) {
    writeLog "ERROR: $pathBuiltAddon was not built."
    exit 1
}
try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($pathBuiltAddon)
    try {
        $lInside = @($archive.Entries | ForEach-Object { $_.FullName })
    } finally {
        $archive.Dispose()
    }
    $iPacked = @($lInside | Where-Object { $_ -like "*.py" }).Count
    # __pycache__ is not source and is never packaged, so it must not be
    # counted on the side that is compared against the package.
    $iOnDisk = @(Get-ChildItem -Path (Join-Path $pathRoot "addon") -Filter "*.py" -Recurse |
        Where-Object { $_.FullName -notlike "*__pycache__*" }).Count
    if ($iPacked -ne $iOnDisk) {
        writeLog "ERROR: $iOnDisk Python files are on disk but $iPacked are in the add-on."
        writeLog "       A module left out builds cleanly and fails on the user's machine."
        # Now the names matter, which is why they were kept rather than only
        # counted. Listing them every time buried everything else in the log.
        $lPackedNames = @($lInside | Where-Object { $_ -like "*.py" } |
            ForEach-Object { Split-Path $_ -Leaf })
        foreach ($fileOnDisk in (Get-ChildItem -Path (Join-Path $pathRoot "addon") -Filter "*.py" -Recurse |
                Where-Object { $_.FullName -notlike "*__pycache__*" })) {
            if ($lPackedNames -notcontains $fileOnDisk.Name) {
                writeLog "       missing from the add-on: $($fileOnDisk.Name)"
            }
        }
        exit 1
    }
    writeLog "All $iPacked Python modules are in the add-on."
} catch {
    # A check that cannot run is worth saying so about. It is not worth
    # stopping a build that has otherwise succeeded, and an earlier version
    # did exactly that: it referred to a variable that did not exist, and the
    # script died where the log stops, with nothing written to say why.
    writeLog "WARNING: the add-on could not be checked: $($_.Exception.Message)"
}

if ($script:bJawsFailed) {
    writeLog "The add-on and the installer were built, and can be installed and tested."
    writeLog "The JAWS scripts did not compile, so this build is NOT ready for tagRelease."
    writeLog "buildHomerView finished with a failure"
    exit 1
}
writeLog "Ready for tagRelease."
writeLog "buildHomerView finished"

# --- Check the setup script before anyone compiles it -----------------------
#
# Inno Setup rejects a directive specified twice and fails on a missing source
# file, both at compile time. Finding either here means the failure is reported
# next to the change that caused it rather than minutes later in another program.

