# cleanDir.ps1
#
# Moves everything the project does not need out of the development directory
# and into C:\temp\HomerView_misc.
#
# Moved, never deleted. A tidying script that deletes is one nobody runs twice,
# and the whole point is that it can be run without thinking about it. Anything
# taken by mistake is sitting in one folder waiting to be moved back.
#
# What is kept is decided by what the setup script installs, what the build
# needs, and what the repository tracks, rather than by a list maintained here
# that would drift from all three.
#
# Pass -bWhatIf to see what would move without moving anything.

param(
    [switch] $bWhatIf,
    [string] $sDestination = "C:\temp\HomerView_misc"
)

$ErrorActionPreference = "Stop"

$pathRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pathLog = Join-Path $pathRoot "cleanDir.log"

function writeLog {
    param([string] $sMessage)
    $sStamped = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $sMessage
    Write-Host $sStamped
    Add-Content -Path $pathLog -Value $sStamped -Encoding UTF8
}

Set-Content -Path $pathLog -Value "" -Encoding UTF8
writeLog "cleanDir starting in $pathRoot"
writeLog "Moving to $sDestination"
if ($bWhatIf) { writeLog "Nothing will actually move: this is a dry run." }
Set-Location $pathRoot

# Files and folders the project needs. Everything else moves.
#
# The documentation is here twice on purpose, as Markdown and as a web page:
# the installer places both, and the web page is what HomerView itself opens.
$lKeepFiles = @(
    ".gitattributes", ".gitignore",
    "README.md", "README.htm",
    "HomerView.md", "HomerView.htm",
    "History.md", "History.htm",
    "Developer.md", "Developer.htm",
    "LICENSE.md",
    "HomerView_setup.iss",
    "buildAddon.cmd", "buildAddon.ps1",
    "buildHomerView.cmd", "buildHomerView.ps1",
    "cleanDir.cmd", "cleanDir.ps1",
    "createHomerViewRepo.cmd", "createHomerViewRepo.ps1",
    "clean.cmd",
    "2htm.exe", "pandoc.exe",
    "installPandoc.cmd", "installPandoc.ps1", "tidyRepo.py",
    "HomerView_setup.exe"
)
$lKeepFolders = @("addon", "build", "docs", "installer", ".git")

# Logs are regenerated on the next run and say nothing anyone needs later.
$lAlwaysMove = @("*.log")

if (-not $bWhatIf) {
    if (-not (Test-Path $sDestination)) {
        New-Item -ItemType Directory -Path $sDestination -Force | Out-Null
        writeLog "Created $sDestination"
    }
}

$iMoved = 0
$iKept = 0

function moveItem {
    param([string] $sName, [string] $sWhy)
    $script:iMoved += 1
    writeLog "Moving $sName  ($sWhy)"
    if ($bWhatIf) { return }
    $pathTarget = Join-Path $sDestination $sName
    # A file of that name already there means this has been run before. Keep
    # both, by putting the date on the newcomer, rather than overwriting
    # something the user may not have looked at yet.
    if (Test-Path $pathTarget) {
        $sStamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $sBase = [System.IO.Path]::GetFileNameWithoutExtension($sName)
        $sExtension = [System.IO.Path]::GetExtension($sName)
        $pathTarget = Join-Path $sDestination "$sBase-$sStamp$sExtension"
        writeLog "  one of those is already there, so this one becomes $(Split-Path $pathTarget -Leaf)"
    }
    try {
        Move-Item -LiteralPath (Join-Path $pathRoot $sName) -Destination $pathTarget -Force
    } catch {
        writeLog "  ERROR: $($_.Exception.Message)"
    }
}

foreach ($item in (Get-ChildItem -Path $pathRoot -Force)) {
    $sName = $item.Name

    if ($item.PSIsContainer) {
        if ($lKeepFolders -contains $sName) {
            $iKept += 1
            continue
        }
        moveItem $sName "not a folder the project uses"
        continue
    }

    $bAlways = $false
    foreach ($sPattern in $lAlwaysMove) {
        if ($sName -like $sPattern) { $bAlways = $true; break }
    }
    if ($bAlways) {
        # The log this script is writing stays where it is.
        if ($sName -eq "cleanDir.log") { $iKept += 1; continue }
        moveItem $sName "a log, regenerated on the next run"
        continue
    }

    if ($lKeepFiles -contains $sName) {
        $iKept += 1
        continue
    }

    moveItem $sName "not installed, not built, not tracked"
}

# The build folder should hold one add-on. Earlier builds wrote a versioned
# copy beside it, and two identical files with different names invites the
# wrong one being picked up.
$pathBuild = Join-Path $pathRoot "build"
if (Test-Path $pathBuild) {
    foreach ($item in (Get-ChildItem -Path $pathBuild -Filter "HomerView-*.nvda-addon" -ErrorAction SilentlyContinue)) {
        $iMoved += 1
        writeLog "Moving build\$($item.Name)  (a versioned copy; the installer uses HomerView.nvda-addon)"
        if (-not $bWhatIf) {
            Move-Item -LiteralPath $item.FullName -Destination (Join-Path $sDestination $item.Name) -Force
        }
    }
}

# Compiled Python, which serves no purpose in a source directory.
foreach ($item in (Get-ChildItem -Path $pathRoot -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue)) {
    writeLog "Removing $($item.FullName)"
    if (-not $bWhatIf) { Remove-Item -LiteralPath $item.FullName -Recurse -Force }
}

writeLog ""
writeLog "Kept $iKept items, moved $iMoved."
if ($bWhatIf) {
    writeLog "Nothing actually moved. Run without -bWhatIf to do it."
} elseif ($iMoved -gt 0) {
    writeLog "Everything moved is in $sDestination and can be moved back."
}
writeLog "cleanDir finished"
