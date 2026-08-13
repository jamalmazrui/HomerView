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
writeLog "Step 1 of 3: checking the setup script and the sources"
writeLog "Checking HomerView_setup.iss"
checkSetupScript
writeLog ""

writeLog "Step 2 of 3: building the add-on"
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

writeLog "Step 3 of 3: compiling the installer"
& $pathCompiler (Join-Path $pathRoot "HomerView_setup.iss")
if ($LASTEXITCODE -ne 0) { writeLog "ERROR: the installer did not compile"; exit 1 }

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

writeLog "Ready for tagRelease."
writeLog "buildHomerView finished"

# --- Check the setup script before anyone compiles it -----------------------
#
# Inno Setup rejects a directive specified twice and fails on a missing source
# file, both at compile time. Finding either here means the failure is reported
# next to the change that caused it rather than minutes later in another program.

