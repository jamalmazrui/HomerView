# installPandoc.ps1 -- make sure pandoc is on this computer, machine-wide.
#
# WHERE IT GOES, AND WHY THAT CHANGED ON 26 SEPTEMBER 2026. This used to copy
# pandoc.exe INTO the HomerView installation folder -- found elsewhere, or
# fetched by winget and then copied. That breaks a standing Homer rule: a tool
# many apps use goes to its own default machine-wide folder and is shared, and
# never into one app's tree, because upgrading that app replaces the folder
# and destroys the tool. EdSharp, FileDir and DbDo already share one pandoc.
#
# So pandoc now lives where its own installer puts it -- Program Files\Pandoc
# -- and HomerView finds it there or on the PATH. The bridge and the add-on
# have always searched both, so nothing else needed to change.
#
# THE ROUTES, in order:
#   1. Already on this computer, anywhere: say so, and update it if winget
#      knows of a newer one.
#   2. winget, machine-wide.
#   3. The latest GitHub release, unpacked into Program Files\Pandoc.
#
# Run by the installer as `installPandoc.cmd noPause`, elevated. Any argument
# is accepted and ignored: this script never waits for a key.
#
# The console says briefly what was found and done. The detail goes to
# %LOCALAPPDATA%\HomerView\logs\HomerView-installPandoc-<stamp>.log.

$ErrorActionPreference = "Continue"

$pathHere = Split-Path -Parent $MyInvocation.MyCommand.Path
$pathLogFolder = Join-Path $env:LOCALAPPDATA "HomerView\logs"
try { New-Item -ItemType Directory -Path $pathLogFolder -Force | Out-Null } catch { }
$pathLog = Join-Path $pathLogFolder ("HomerView-installPandoc-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")
$pathMachine = Join-Path $env:ProgramFiles "Pandoc"
$c_sWingetId = "JohnMacFarlane.Pandoc"

function writeLog {
    param([string] $sMessage)
    $sStamped = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $sMessage
    try { Add-Content -Path $pathLog -Value $sStamped -Encoding UTF8 } catch { }
}

function say {
    param([string] $sMessage)
    Write-Host $sMessage
    writeLog $sMessage
}

function findPandoc {
    $oCommand = Get-Command "pandoc.exe" -ErrorAction SilentlyContinue
    if ($oCommand) { return $oCommand.Source }
    foreach ($sCandidate in @(
        (Join-Path $pathMachine "pandoc.exe"),
        "$env:LOCALAPPDATA\Pandoc\pandoc.exe",
        "${env:ProgramFiles(x86)}\Pandoc\pandoc.exe")) {
        if ($sCandidate -and (Test-Path $sCandidate)) { return $sCandidate }
    }
    return ""
}

function versionOf {
    param([string] $sExe)
    try {
        $sFirst = (& $sExe --version 2>&1 | Select-Object -First 1 | Out-String).Trim()
        return $sFirst
    } catch {
        return "(version could not be read)"
    }
}

writeLog "--- installPandoc ---"
writeLog "  script: $($MyInvocation.MyCommand.Path)"
writeLog "  PowerShell: $($PSVersionTable.PSVersion)"
writeLog "  platform: $([System.Environment]::OSVersion.VersionString)"
writeLog "  working directory: $(Get-Location)"
writeLog "  command line: $($MyInvocation.Line)"
writeLog "  machine-wide target: $pathMachine"

$bWinget = [bool] (Get-Command "winget.exe" -ErrorAction SilentlyContinue)
writeLog "  winget available: $bWinget"

# --- 1. already here --------------------------------------------------------
$sFound = findPandoc
if ($sFound) {
    writeLog "Found $sFound, $(versionOf $sFound)"
    if ($bWinget) {
        writeLog "Running: winget upgrade --id $c_sWingetId --exact"
        $sOutput = & winget upgrade --id $c_sWingetId --exact --accept-package-agreements `
            --accept-source-agreements --disable-interactivity 2>&1 | Out-String
        writeLog "winget exit code $LASTEXITCODE"
        foreach ($sLine in ($sOutput -split "`n")) { if ($sLine.Trim()) { writeLog "  $($sLine.Trim())" } }
    }
    $sFound = findPandoc
    say "Pandoc is installed: $(versionOf $sFound)"
    exit 0
}

# --- 2. winget, machine-wide ------------------------------------------------
if ($bWinget) {
    say "Installing pandoc with winget..."
    writeLog "Running: winget install --id $c_sWingetId --exact --scope machine"
    $sOutput = & winget install --id $c_sWingetId --exact --scope machine --accept-package-agreements `
        --accept-source-agreements --disable-interactivity 2>&1 | Out-String
    writeLog "winget exit code $LASTEXITCODE"
    foreach ($sLine in ($sOutput -split "`n")) { if ($sLine.Trim()) { writeLog "  $($sLine.Trim())" } }
    # winget changes the PATH for new processes, not this one, so look by folder.
    $sFound = findPandoc
    if ($sFound) {
        say "Pandoc installed: $(versionOf $sFound)"
        exit 0
    }
    writeLog "winget finished but pandoc.exe is not where it should be"
}

# --- 3. the GitHub release, into Program Files\Pandoc -----------------------
say "Fetching pandoc from its GitHub release..."
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $sApi = "https://api.github.com/repos/jgm/pandoc/releases/latest"
    writeLog "Asking $sApi which assets the latest release has"
    $dRelease = Invoke-RestMethod -Uri $sApi -Headers @{ "User-Agent" = "HomerView" } -TimeoutSec 60
    $oAsset = $dRelease.assets | Where-Object { $_.name -like "*windows-x86_64.zip" } | Select-Object -First 1
    if (-not $oAsset) { throw "the release has no Windows zip attached" }
    writeLog "Downloading $($oAsset.name), $([math]::Round($oAsset.size / 1MB, 1)) MB"
    $pathZip = Join-Path $env:TEMP $oAsset.name
    Invoke-WebRequest -Uri $oAsset.browser_download_url -OutFile $pathZip -UseBasicParsing -TimeoutSec 900
    $pathUnpack = Join-Path $env:TEMP "pandocUnpack"
    if (Test-Path $pathUnpack) { Remove-Item $pathUnpack -Recurse -Force }
    Expand-Archive -LiteralPath $pathZip -DestinationPath $pathUnpack -Force
    $oExe = Get-ChildItem -Path $pathUnpack -Filter "pandoc.exe" -Recurse | Select-Object -First 1
    if (-not $oExe) { throw "pandoc.exe was not in the archive" }
    New-Item -ItemType Directory -Path $pathMachine -Force | Out-Null
    Copy-Item -Path (Join-Path $oExe.DirectoryName "*") -Destination $pathMachine -Recurse -Force
    writeLog "Unpacked into $pathMachine"
    Remove-Item $pathZip -Force -ErrorAction SilentlyContinue
    Remove-Item $pathUnpack -Recurse -Force -ErrorAction SilentlyContinue
    say "Pandoc installed: $(versionOf (Join-Path $pathMachine 'pandoc.exe'))"
    exit 0
} catch {
    writeLog "ERROR: $($_.Exception.Message)"
    say "Pandoc could not be installed automatically. HomerView works without it;"
    say "only ebooks, Markdown and OpenDocument text need it. The log is:"
    say "  $pathLog"
    exit 1
}
