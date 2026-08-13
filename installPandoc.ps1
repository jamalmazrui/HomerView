# installPandoc.ps1
#
# Fetches pandoc and puts pandoc.exe in the HomerView installation folder.
#
# HomerView uses pandoc for ebooks, Markdown and OpenDocument text. It is not
# packaged with HomerView because it is about 220 megabytes, which GitHub will
# not accept and which is a long download to impose on someone who may already
# have it or may never open one of those formats.
#
# Three ways of getting it, in the order most likely to work:
#
#   1. A copy already on this machine, which is copied rather than downloaded.
#      Someone with pandoc installed should not download it again.
#   2. winget, which ships with Windows 10 and 11 and handles the download,
#      the verification and the unpacking.
#   3. The release on GitHub, fetched and unpacked here, for a machine where
#      winget is absent or declines.
#
# Writes installPandoc.log beside this script.

$ErrorActionPreference = "Stop"

$pathRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pathLog = Join-Path $pathRoot "installPandoc.log"
$pathTarget = Join-Path $pathRoot "pandoc.exe"

function writeLog {
    param([string] $sMessage)
    $sStamped = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $sMessage
    Write-Host $sStamped
    try { Add-Content -Path $pathLog -Value $sStamped -Encoding UTF8 } catch { }
}

Set-Content -Path $pathLog -Value "" -Encoding UTF8
writeLog "installPandoc starting"
writeLog "  script: $($MyInvocation.MyCommand.Path)"
writeLog "  PowerShell: $($PSVersionTable.PSVersion)"
writeLog "  platform: $([System.Environment]::OSVersion.VersionString)"
writeLog "  working directory: $(Get-Location)"
writeLog "  target: $pathTarget"

if (Test-Path $pathTarget) {
    $nSize = [math]::Round((Get-Item $pathTarget).Length / 1MB, 1)
    writeLog "pandoc.exe is already here, $nSize MB. Nothing to do."
    Write-Host ""
    Write-Host "Pandoc is already installed. You can close this window."
    exit 0
}

# 1. Already on the machine.
writeLog "Looking for a copy already installed"
$sFound = ""
$command = Get-Command "pandoc.exe" -ErrorAction SilentlyContinue
if ($command) { $sFound = $command.Source }
if (-not $sFound) {
    foreach ($sCandidate in @(
        "$env:LOCALAPPDATA\Pandoc\pandoc.exe",
        "$env:ProgramFiles\Pandoc\pandoc.exe",
        "${env:ProgramFiles(x86)}\Pandoc\pandoc.exe")) {
        if (Test-Path $sCandidate) { $sFound = $sCandidate; break }
    }
}
if ($sFound) {
    writeLog "Found $sFound; copying rather than downloading"
    try {
        Copy-Item -LiteralPath $sFound -Destination $pathTarget -Force
        writeLog "Copied. $([math]::Round((Get-Item $pathTarget).Length / 1MB, 1)) MB"
        Write-Host ""
        Write-Host "Pandoc was already on this computer and has been copied into place."
        exit 0
    } catch {
        writeLog "The copy failed: $($_.Exception.Message)"
    }
}

# 2. winget.
writeLog "Trying winget"
if (Get-Command "winget.exe" -ErrorAction SilentlyContinue) {
    try {
        writeLog "Running: winget install --id JohnMacFarlane.Pandoc"
        $sOutput = & winget install --id JohnMacFarlane.Pandoc --accept-package-agreements `
            --accept-source-agreements --disable-interactivity 2>&1 | Out-String
        writeLog "winget exit code $LASTEXITCODE"
        foreach ($sLine in ($sOutput -split "`n")) {
            if ($sLine.Trim()) { writeLog "  $($sLine.Trim())" }
        }
        # winget installs it elsewhere; the copy into place is still needed.
        foreach ($sCandidate in @(
            "$env:LOCALAPPDATA\Pandoc\pandoc.exe",
            "$env:ProgramFiles\Pandoc\pandoc.exe")) {
            if (Test-Path $sCandidate) {
                Copy-Item -LiteralPath $sCandidate -Destination $pathTarget -Force
                writeLog "Copied from $sCandidate"
                Write-Host ""
                Write-Host "Pandoc installed."
                exit 0
            }
        }
        writeLog "winget reported success but pandoc.exe was not where expected"
    } catch {
        writeLog "winget failed: $($_.Exception.Message)"
    }
} else {
    writeLog "winget is not on this machine"
}

# 3. The GitHub release.
writeLog "Falling back to the GitHub release"
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $sApi = "https://api.github.com/repos/jgm/pandoc/releases/latest"
    writeLog "Asking $sApi which assets the latest release has"
    $dRelease = Invoke-RestMethod -Uri $sApi -Headers @{ "User-Agent" = "HomerView" } -TimeoutSec 60
    # The Windows zip, rather than the installer, because a zip can be unpacked
    # here without a second elevation prompt.
    $asset = $dRelease.assets | Where-Object { $_.name -like "*windows-x86_64.zip" } | Select-Object -First 1
    if (-not $asset) { throw "The release has no Windows zip attached" }
    writeLog "Downloading $($asset.name), $([math]::Round($asset.size / 1MB, 1)) MB"

    $pathZip = Join-Path $env:TEMP $asset.name
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $pathZip -UseBasicParsing -TimeoutSec 900
    writeLog "Downloaded to $pathZip"

    $pathUnpack = Join-Path $env:TEMP "pandocUnpack"
    if (Test-Path $pathUnpack) { Remove-Item $pathUnpack -Recurse -Force }
    Expand-Archive -LiteralPath $pathZip -DestinationPath $pathUnpack -Force
    $found = Get-ChildItem -Path $pathUnpack -Filter "pandoc.exe" -Recurse | Select-Object -First 1
    if (-not $found) { throw "pandoc.exe was not in the archive" }

    Copy-Item -LiteralPath $found.FullName -Destination $pathTarget -Force
    writeLog "Installed $pathTarget, $([math]::Round((Get-Item $pathTarget).Length / 1MB, 1)) MB"
    Remove-Item $pathZip -Force -ErrorAction SilentlyContinue
    Remove-Item $pathUnpack -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host ""
    Write-Host "Pandoc installed. You can close this window."
    exit 0
} catch {
    writeLog "ERROR: $($_.Exception.Message)"
    Write-Host ""
    Write-Host "Pandoc could not be installed automatically."
    Write-Host "Download it from https://pandoc.org and put pandoc.exe in:"
    Write-Host "  $pathRoot"
    Write-Host ""
    Write-Host "HomerView works without it; only ebooks, Markdown and OpenDocument"
    Write-Host "text need it, and LibreOffice covers most other formats."
    exit 1
}
