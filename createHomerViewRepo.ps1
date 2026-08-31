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

function runGit {
    <#
    Run git and return its output, treating a non-zero exit as an answer
    rather than a catastrophe.

    This function exists because of one PowerShell behaviour. With
    ErrorActionPreference set to Stop, anything a native program writes to
    standard error becomes a terminating error. git writes "No such remote
    'origin'" to standard error, and that is not a failure: it is the correct
    answer to "is there an origin yet". Redirecting to $null does not help,
    because PowerShell raises NativeCommandError before the redirect matters.
    Lowering the preference around the call, and judging the result by the
    exit code as git intends, is the only reliable way.
    #>
    param([string[]] $lArguments, [switch] $bQuiet)

    $sPrevious = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $sOutput = (& git @lArguments 2>&1 | Out-String).Trim()
        $iExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $sPrevious
    }
    if ($iExit -ne 0 -and -not $bQuiet) {
        writeLog "git $($lArguments -join ' ') exited with $iExit"
        if ($sOutput) { writeLog "  $sOutput" }
    }
    return [pscustomobject]@{ Output = $sOutput; ExitCode = $iExit; Ok = ($iExit -eq 0) }
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
$bOversize = $false
foreach ($file in (Get-ChildItem -Path $pathRoot -Recurse -File -ErrorAction SilentlyContinue)) {
    if ($file.FullName -like "*\.git\*") { continue }
    if ($file.Length -gt 95MB) {
        $bOversize = $true
        writeLog "WARNING: $($file.Name) is $([math]::Round($file.Length/1MB)) MB, which GitHub will refuse."
        writeLog "         Add it to .gitignore, or track it with: git lfs track `"$($file.Name)`""
    }
}

if ($bOversize) {
    writeLog "One or more files exceed GitHub's limit. Deal with those before pushing,"
    writeLog "or the push will be rejected after everything else has succeeded."
}

if (-not (Test-Path (Join-Path $pathRoot ".git"))) {
    writeLog "Creating the repository"
    $result = runGit @("init", "--initial-branch=main")
    if (-not $result.Ok) { writeLog "ERROR: the repository could not be created"; exit 1 }
} else {
    writeLog "A repository already exists here"
}

if (-not (Test-Path (Join-Path $pathRoot ".gitignore"))) {
    writeLog "ERROR: .gitignore is missing. It should ship with the project."
    exit 1
}

writeLog "Staging"
$result = runGit @("add", "--all")
if (-not $result.Ok) { writeLog "ERROR: staging failed"; exit 1 }

$result = runGit @("status", "--porcelain")
if ($result.Output) {
    $sMessage = if ($bPushOnly) { "Update" } else { "HomerView: NVDA, Microsoft Edge and the DevTools Protocol together" }
    writeLog "Committing"
    $result = runGit @("commit", "-m", $sMessage)
    if (-not $result.Ok) { writeLog "ERROR: the commit failed"; exit 1 }
} else {
    writeLog "Nothing to commit"
}

# No origin yet is the normal state on a first run, so ask quietly.
$result = runGit @("remote", "get-url", "origin") -bQuiet
$sOrigin = if ($result.Ok) { $result.Output } else { "" }
if (-not $sOrigin) {
    $sVisibility = if ($bPrivate) { "--private" } else { "--public" }
    writeLog "Creating the GitHub repository $sRemoteName ($sVisibility)"
    gh repo create $sRemoteName $sVisibility --source=. --remote=origin --description "An NVDA add-on that drives Microsoft Edge through the Chrome DevTools Protocol"
} else {
    writeLog "Origin is already $sOrigin"
}

writeLog "Pushing"
$result = runGit @("push", "--set-upstream", "origin", "main")
if (-not $result.Ok) {
    writeLog "ERROR: the push failed. The message above says why."
    writeLog "A file over 100 megabytes is the usual cause; see the warnings near the top."
    exit 1
}
$result = runGit @("remote", "get-url", "origin") -bQuiet
writeLog "Repository: $($result.Output)"
writeLog "createHomerViewRepo finished"
