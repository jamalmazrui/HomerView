# buildAll.ps1
# Builds everything a release needs, in the order tagRelease expects:
# the add-on package, then the installer whose version resource tagRelease reads.
# Writes buildAll.log beside itself.

$ErrorActionPreference = "Stop"

$pathRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pathLog = Join-Path $pathRoot "buildAll.log"

function writeLog {
    param([string] $sMessage)
    $sStamped = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $sMessage
    Write-Host $sStamped
    Add-Content -Path $pathLog -Value $sStamped -Encoding UTF8
}

Set-Content -Path $pathLog -Value "" -Encoding UTF8
writeLog "buildAll starting in $pathRoot"
Set-Location $pathRoot

writeLog "Step 1 of 2: building the add-on"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $pathRoot "buildAddon.ps1")
if ($LASTEXITCODE -ne 0) { writeLog "ERROR: the add-on build failed"; exit 1 }

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

writeLog "Step 2 of 2: compiling the installer"
& $pathCompiler (Join-Path $pathRoot "HomerView_setup.iss")
if ($LASTEXITCODE -ne 0) { writeLog "ERROR: the installer did not compile"; exit 1 }

$pathInstaller = Join-Path $pathRoot "HomerView_setup.exe"
if (-not (Test-Path $pathInstaller)) {
    writeLog "ERROR: HomerView_setup.exe was not produced. Check OutputDir in the setup script."
    exit 1
}
$sVersion = (Get-Item $pathInstaller).VersionInfo.FileVersion
writeLog "Built HomerView_setup.exe, version $sVersion, $([math]::Round((Get-Item $pathInstaller).Length/1MB,1)) MB"
writeLog "Ready for tagRelease."
writeLog "buildAll finished"

# --- Check the setup script before anyone compiles it -----------------------
#
# Inno Setup rejects a directive specified twice and fails on a missing source
# file, both at compile time. Finding either here means the failure is reported
# next to the change that caused it rather than minutes later in another program.

writeLog "Checking HomerView_setup.iss"
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
