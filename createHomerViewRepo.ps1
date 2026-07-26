# createHomerViewRepo.ps1
# Creates the HomerView Git repository, connects it to GitHub, and pushes.
# Writes createHomerViewRepo.log beside itself.
#
# Safe to run more than once. Every step checks whether it has already been
# done, so a second run adds what is missing rather than failing or duplicating.

param(
    [string] $sRemoteName = "HomerView",
    [switch] $bPrivate,
    [switch] $bPushOnly
)

$ErrorActionPreference = "Stop"

$pathRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pathLog = Join-Path $pathRoot "createHomerViewRepo.log"

function writeLog {
    param([string] $sMessage)
    $sStamped = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $sMessage
    Write-Host $sStamped
    Add-Content -Path $pathLog -Value $sStamped -Encoding UTF8
}

function requireTool {
    param([string] $sName, [string] $sWhere)
    if (-not (Get-Command $sName -ErrorAction SilentlyContinue)) {
        writeLog "ERROR: $sName was not found. Install it from $sWhere"
        exit 1
    }
    writeLog "Found $sName"
}

Set-Content -Path $pathLog -Value "" -Encoding UTF8
writeLog "createHomerViewRepo starting in $pathRoot"

requireTool "git" "https://git-scm.com"
requireTool "gh" "https://cli.github.com"

Set-Location $pathRoot

# GitHub refuses a single file over 100 megabytes. Saying so before the push
# fails is worth more than explaining the rejection afterwards.
foreach ($file in (Get-ChildItem -Path $pathRoot -Recurse -File -ErrorAction SilentlyContinue)) {
    if ($file.FullName -like "*\.git\*") { continue }
    if ($file.Length -gt 95MB) {
        writeLog "WARNING: $($file.Name) is $([math]::Round($file.Length/1MB)) MB, which GitHub will refuse."
        writeLog "         Add it to .gitignore, or track it with: git lfs track `"$($file.Name)`""
    }
}

if (-not (Test-Path (Join-Path $pathRoot ".git"))) {
    writeLog "Creating the repository"
    git init --initial-branch=main | Out-Null
} else {
    writeLog "A repository already exists here"
}

if (-not (Test-Path (Join-Path $pathRoot ".gitignore"))) {
    writeLog "ERROR: .gitignore is missing. It should ship with the project."
    exit 1
}

writeLog "Staging"
git add --all
$sStatus = git status --porcelain
if ($sStatus) {
    $sMessage = if ($bPushOnly) { "Update" } else { "HomerView: NVDA, Microsoft Edge and the DevTools Protocol together" }
    writeLog "Committing"
    git commit -m $sMessage | Out-Null
} else {
    writeLog "Nothing to commit"
}

$sOrigin = (git remote get-url origin 2>$null)
if (-not $sOrigin) {
    $sVisibility = if ($bPrivate) { "--private" } else { "--public" }
    writeLog "Creating the GitHub repository $sRemoteName ($sVisibility)"
    gh repo create $sRemoteName $sVisibility --source=. --remote=origin --description "An NVDA add-on that drives Microsoft Edge through the Chrome DevTools Protocol"
} else {
    writeLog "Origin is already $sOrigin"
}

writeLog "Pushing"
git push --set-upstream origin main
writeLog "Repository: $(git remote get-url origin)"
writeLog "createHomerViewRepo finished"
