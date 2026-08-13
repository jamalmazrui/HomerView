# buildAddon.ps1
# Packages the addon folder into build\HomerView.nvda-addon.
#
# The stable name is what the installer references, so HomerView_setup.iss never
# has to be edited when the version changes. Coupling the two meant every bump
# needed two edits, and forgetting one would break the installer at compile time
# for a reason that had nothing to do with what had changed.
#
# One file, not two. A versioned copy was written here as well, for release
# assets, and it was a mistake: two identical files with different names in one
# folder invites the wrong one being picked up, and the version is already in
# the manifest, which is what NVDA reads.
# All output is written to buildAddon.log as well as the console.

$ErrorActionPreference = "Stop"

$pathRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pathAddon = Join-Path $pathRoot "addon"
$pathBuild = Join-Path $pathRoot "build"
$pathLog = Join-Path $pathRoot "buildAddon.log"

function writeLog {
    param([string] $sMessage)
    $sStamped = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $sMessage
    Write-Host $sStamped
    Add-Content -Path $pathLog -Value $sStamped -Encoding UTF8
}

Set-Content -Path $pathLog -Value "" -Encoding UTF8
writeLog "HomerView add-on build started"

if (-not (Test-Path $pathAddon)) {
    writeLog "ERROR: the addon folder was not found at $pathAddon"
    exit 1
}

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
            "ReadMe.htm", "hotkeys.htm", "readme.html")
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
    writeLog "Including $($pathFile.FullName.Substring($pathAddon.Length + 1))"
}

Compress-Archive -Path (Join-Path $pathAddon "*") -DestinationPath "$pathOutput.zip" -Force
Move-Item "$pathOutput.zip" $pathOutput -Force
writeLog "Wrote $pathOutput"


writeLog "HomerView add-on build finished"
