# release.ps1 -- part of the Homer Development Kit.
#
# Tag, push, and publish a GitHub Release for the program in the current
# directory. Generic: works for EdSharp, FileDir, DbDo, HomerView, HomerScribe
# or any sibling app without editing this script.
#
# WHERE IT LIVES. The script acts on the CURRENT DIRECTORY, never on its own
# location, so one copy in a tools folder on the PATH serves every project:
#
#     C:\bin\release.cmd
#     C:\bin\release.ps1
#
#     cd C:\EdSharp
#     release
#
# or, without changing directory, name the repo:
#
#     release -Path C:\EdSharp
#
# A copy beside the project works exactly as it always has.
#
# TWO KINDS OF PROJECT. An app with an installer is released from the version
# stamped into <App>_setup.exe, with that installer attached as the release
# asset. A project that ships SOURCE and has no <App>_setup.iss -- HomerDev is
# one -- is released from version.txt, with no asset. Everything else is the
# same. An earlier edition stopped with "Could not find <App>_setup.iss", which
# is what made HomerDev unreleasable.
#
# Discovery (nothing is hardcoded):
#   * App      -- the name of the current directory. C:\FileDir yields "FileDir".
#   * Setup    -- the matching "<App>_setup.iss" (case-insensitive).
#   * Installer -- "<App>_setup.exe", named from the .iss OutputBaseFilename so
#                  the asset name always matches what the .iss actually produces
#                  (this is the name the F11 Elevate Version command downloads,
#                  and GitHub asset URLs are case-sensitive).
#   * Version  -- read from the .iss. Both Inno styles are supported:
#                  a [Setup] directive   AppVersion=5.0            (EdSharp, FileDir)
#                  a preprocessor define #define AppVersion "1.0.126"  (DbDo)
#   * Owner/repo -- parsed from the git "origin" remote, so the public download
#                  URL is right even if the GitHub repo name differs in case
#                  from the local folder.
#
# VERSION HANDLING. The build assigns the version: build<App>.cmd steps
# version.txt, writes it into the program and compiles the installer, which
# stamps it into <App>_setup.exe. This script never changes a version number.
# It tags and publishes the number stamped in the installer, because that is the
# file that ships, and it STOPS, publishing nothing, when:
#   * the installer is missing (it looks at the top of the project, then in
#     exec, where some apps wrote it before the Homer layout settled);
#   * the installer carries a LOWER number than version.txt -- the last build
#     stepped the version but did not finish a new installer, so the one on disk
#     is an older build (HomerView 1.48.53 was published on 26 September 2026
#     while version.txt said 1.48.63). -Force publishes it anyway;
#   * scripts\check, when the project has it, reports a problem. -NoCheck skips
#     it.
# Releasing a version that is already on GitHub publishes nothing and says what
# to do instead.
#
# QUIET QUESTIONS. Asking git or gh whether something exists is a question, and
# "no" is a normal answer. Windows PowerShell 5.1 turns any line a native
# program writes to stderr into an error record -- "NativeCommandError" -- even
# with 2>$null, and the transcript prints each one, so a successful release read
# like a failing one. Such questions now go through cmd, which discards the
# stderr before PowerShell sees it.
#
# Working tree: uncommitted changes never block a release. They are listed, so
# a release made from a changed tree is at least never a surprise.
#
# Requirements: git and gh in PATH, gh authenticated (gh auth login),
# PowerShell 5.1+.
#
# This is a maintainer script. Keep release.ps1, release.cmd, and
# logs/ in .gitignore so they stay out of the source browser.

# Note: the parameters that receive the .iss text are marked AllowEmptyString /
# AllowEmptyCollection. A PowerShell [Parameter(Mandatory)] on a [string[]] is
# implicitly ValidateNotNullOrEmpty on EVERY element, and an .iss naturally has
# blank lines, so without those attributes binding fails with "Cannot bind
# argument to parameter 'aLines' because it is an empty string."

[CmdletBinding()]
param(
    [string] $Path,
    [string] $Version,
    [switch] $NoBump,
    [switch] $NoCommit,
    [switch] $SkipStaleCheck,
    [switch] $Force,
    [switch] $NoCheck
)

$ErrorActionPreference = 'Stop'

# The repo is the CURRENT DIRECTORY unless -Path names another, so a single
# copy in a tools folder on the PATH -- C:\bin\release.cmd -- serves every
# project. The script's own location is never used to find the repo.
$sRepoPath = $PWD.Path
if ($Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        Write-Host "ERROR: -Path $Path is not a folder." -ForegroundColor Red
        exit 1
    }
    $sRepoPath = (Resolve-Path -LiteralPath $Path).Path
    Set-Location -LiteralPath $sRepoPath
}
# THE LOG GOES IN THE PROJECT'S logs FOLDER, one file per release run, named as
# the program names its runtime logs: <App>-release-yyyyMMdd-HHmmss.log. An
# alphabetical sort is then a chronological one, and zipping logs gathers every
# build, clean, tidy and release together. It used to be release.log at the
# top of the project, overwritten on every run.
$sLogDir = Join-Path $sRepoPath 'logs'
if (-not (Test-Path -LiteralPath $sLogDir)) { New-Item -ItemType Directory -Path $sLogDir | Out-Null }
$sLogPath = Join-Path $sLogDir ((Split-Path -Leaf $sRepoPath) + '-release-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')

try {
    Start-Transcript -LiteralPath $sLogPath -Force | Out-Null
} catch {
    Write-Host "ERROR: Could not start transcript at $sLogPath" -ForegroundColor Red
    Write-Host $_
    exit 1
}

# ============================================================
# Helpers
# ============================================================

function getIssPath {
    # Find "<App>_setup.iss" for the app named by the current directory.
    # Case-insensitive, so C:\EdSharp matches edsharp_setup.iss.
    param(
        [Parameter(Mandatory)] [string] $sPath,
        [Parameter(Mandatory)] [string] $sApp
    )
    $sPattern = "$($sApp)_setup.iss"
    $aFound = @(Get-ChildItem -LiteralPath $sPath -Filter $sPattern -File -ErrorAction SilentlyContinue)
    if ($aFound.Count -eq 1) { return $aFound[0].FullName }
    if ($aFound.Count -gt 1) {
        $sList = ($aFound | ForEach-Object { $_.Name }) -join ', '
        throw "More than one setup script matches $sPattern ($sList)."
    }
    # NO SETUP SCRIPT IS A VALID ANSWER, not an error. A repository that ships
    # source rather than an installer -- HomerDev is one -- still deserves a tag
    # and a release. The caller decides what to do with the empty answer.
    return ''
}

function getIssDirective {
    # Return the value of an Inno [Setup] directive, e.g. OutputBaseFilename.
    # Resolves the {#Token} idiom against a matching #define when present.
    param(
        [Parameter(Mandatory)] [AllowEmptyCollection()] [AllowEmptyString()] [string[]] $aLines,
        [Parameter(Mandatory)] [string]   $sName
    )
    $sValue = ''
    foreach ($sLine in $aLines) {
        if ($sLine -match "^\s*$([regex]::Escape($sName))\s*=\s*(.+?)\s*$") {
            $sValue = $Matches[1]
            break
        }
    }
    if ($sValue -eq '') { return '' }
    # Resolve {#SomeDefine} references against the #define lines.
    while ($sValue -match '\{#(\w+)\}') {
        $sToken = $Matches[1]
        $sResolved = ''
        foreach ($sLine in $aLines) {
            if ($sLine -match "^\s*#define\s+$([regex]::Escape($sToken))\s+`"([^`"]*)`"") {
                $sResolved = $Matches[1]
                break
            }
        }
        if ($sResolved -eq '') { break }
        $sValue = $sValue -replace "\{#$([regex]::Escape($sToken))\}", $sResolved
    }
    return $sValue
}

function runNative {
    # Run a program with its standard output and error captured, never shown
    # to PowerShell as a stream, and return @{ Code = exit code; Out = the
    # output }. System.Diagnostics.Process rather than & or cmd /c: Windows
    # PowerShell 5.1 turns each stderr line of a native program into a
    # NativeCommandError, even with 2>$null, and routing through cmd /c needs
    # quoting that 5.1 mangles -- the first release of this edition died on
    # "The syntax of the command is incorrect" before it could say more.
    param(
        [Parameter(Mandatory)] [string]   $sExe,
        [AllowEmptyCollection()] [string[]] $aArgs = @()
    )
    $oCommand = Get-Command $sExe -ErrorAction SilentlyContinue | Select-Object -First 1
    $sPath = if ($oCommand -and $oCommand.Source) { $oCommand.Source } else { $sExe }
    $oInfo = New-Object System.Diagnostics.ProcessStartInfo
    $sArgs = ($aArgs | ForEach-Object { if ($_ -match '[\s"]') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ } }) -join ' '
    # A .cmd or .bat (gh can be gh.cmd) runs through cmd, quoted whole so a
    # path with a space survives: cmd /s strips exactly the outer pair.
    if ($sPath -match '\.(cmd|bat)$') {
        $oInfo.FileName = $env:ComSpec
        $oInfo.Arguments = '/d /s /c ""' + $sPath + '" ' + $sArgs + '"'
    } else {
        $oInfo.FileName = $sPath
        $oInfo.Arguments = $sArgs
    }
    $oInfo.UseShellExecute = $false
    $oInfo.RedirectStandardOutput = $true
    $oInfo.RedirectStandardError = $true
    $oInfo.CreateNoWindow = $true
    $oInfo.WorkingDirectory = (Get-Location).Path
    try {
        $oProcess = [System.Diagnostics.Process]::Start($oInfo)
    } catch {
        return @{ Code = 9009; Out = "Could not start ${sExe}: $($_.Exception.Message)" }
    }
    # Both streams are read at once, so a program filling one cannot stall on
    # the other.
    $oErrTask = $oProcess.StandardError.ReadToEndAsync()
    $sOut = $oProcess.StandardOutput.ReadToEnd()
    $oProcess.WaitForExit()
    $sErr = $oErrTask.Result
    return @{ Code = $oProcess.ExitCode; Out = (($sOut + $sErr) -replace "`r", '').TrimEnd() }
}

function invokeQuiet {
    # A yes-or-no question to git or gh: the exit code, nothing shown.
    param(
        [Parameter(Mandatory)] [string]   $sExe,
        [Parameter(Mandatory)] [string[]] $aArgs
    )
    return (runNative -sExe $sExe -aArgs $aArgs).Code
}

function readQuiet {
    # A program's output as text, with nothing shown and no error records.
    param(
        [Parameter(Mandatory)] [string]   $sExe,
        [Parameter(Mandatory)] [string[]] $aArgs
    )
    $oResult = runNative -sExe $sExe -aArgs $aArgs
    if ($oResult.Code -ne 0) { return '' }
    return $oResult.Out.Trim()
}

function getOwnerRepo {
    # Parse "owner/repo" from the origin remote, covering both HTTPS and SSH
    # forms. The remote is authoritative: the GitHub repo may differ in case
    # from the local folder, and asset URLs are case-sensitive.
    $sUrl = readQuiet -sExe 'git' -aArgs @('config', '--get', 'remote.origin.url')
    if (-not $sUrl) { throw "No 'origin' remote is configured, so the GitHub owner/repo cannot be determined." }
    $sTrimmed = $sUrl -replace '\.git$', ''
    if ($sTrimmed -match '[:/]([^/:]+)/([^/]+)$') {
        return "$($Matches[1])/$($Matches[2])"
    }
    throw "Could not parse owner/repo from the origin remote: $sUrl"
}

function sameVersion {
    # Compare two dotted-numeric versions, padding with zeros, so 5.0.2 and
    # 5.0.2.0 (the form Windows reports for a file's version resource) match.
    param([string] $sA, [string] $sB)
    if (-not $sA -or -not $sB) { return $false }
    $aA = @($sA.Trim().Split('.')); $aB = @($sB.Trim().Split('.'))
    for ($i = 0; $i -lt 4; $i++) {
        $iA = 0; $iB = 0
        if ($i -lt $aA.Count) { [void][int]::TryParse($aA[$i], [ref] $iA) }
        if ($i -lt $aB.Count) { [void][int]::TryParse($aB[$i], [ref] $iB) }
        if ($iA -ne $iB) { return $false }
    }
    return $true
}

function isReleased {
    # Has this tag already been published?  Asks GitHub first (authoritative,
    # and covers a release made from another machine), then falls back to a
    # local tag.  This is what lets the script decide by itself whether the
    # version in the .iss still needs releasing or has been used already.
    param([Parameter(Mandatory)] [string] $sTag)
    # GITHUB DECIDES, AND ONLY GITHUB (1.43.12). A tag on this machine alone
    # means an earlier run stopped between tagging and publishing -- on
    # 26 September 2026 EdSharp's release said "v5.0.14 is already on GitHub"
    # while its build, which steps over every number tagged on origin, had
    # just used 5.0.14. The tag step below pushes such a tag and publishes.
    # Without gh there is no way to ask GitHub, so a local tag is the answer.
    if (Get-Command gh -ErrorAction SilentlyContinue) {
        # THE LIST OF RELEASES, READ AS DATA (1.43.13). Asking "gh release view"
        # and trusting its exit code said EdSharp 5.0.15 was on GitHub minutes
        # after the build, which steps over every tagged number, had chosen it:
        # gh here is gh.cmd, and a batch file's exit code through cmd is not a
        # reliable answer. The tag names GitHub lists are. Only when the list
        # cannot be read does the exit code decide, as before.
        $oList = runNative -sExe 'gh' -aArgs @('release', 'list', '--limit', '1000', '--json', 'tagName,isDraft')
        if ($oList.Code -eq 0 -and $oList.Out) {
            try {
                $lReleases = @($oList.Out | ConvertFrom-Json)
                foreach ($oRelease in $lReleases) {
                    if ($oRelease.tagName -eq $sTag -and -not $oRelease.isDraft) { return $true }
                }
                return $false
            } catch {
                Write-Host "NOTE: the release list could not be read ($($_.Exception.Message)); asking for $sTag alone." -ForegroundColor Yellow
            }
        }
        # A missing release is a normal answer, not an error.
        return ((invokeQuiet -sExe 'gh' -aArgs @('release', 'view', $sTag)) -eq 0)
    }
    if ((invokeQuiet -sExe 'git' -aArgs @('rev-parse', '--verify', '--quiet', "refs/tags/$sTag")) -eq 0) { return $true }
    return $false
}

function invokeChecked {
    # Run an external program; show output; throw on a non-zero exit.
    param(
        [Parameter(Mandatory)] [string]   $sExe,
        [Parameter(Mandatory)] [string[]] $aArgs,
        [string]                          $sLabel = $null
    )
    if (-not $sLabel) { $sLabel = "$sExe $($aArgs -join ' ')" }
    Write-Host "  > $sLabel" -ForegroundColor DarkGray
    $ErrorActionPreference = 'Continue'
    & $sExe @aArgs
    $iCode = $LASTEXITCODE
    if ($iCode -ne 0) { throw "Command failed (exit $iCode): $sLabel" }
}

function tryInvoke {
    # Run an external program; return the exit code, never throw. Used to ASK
    # whether something exists, where a non-zero exit is a valid "no".
    param(
        [Parameter(Mandatory)] [string]   $sExe,
        [Parameter(Mandatory)] [string[]] $aArgs
    )
    return (invokeQuiet -sExe $sExe -aArgs $aArgs)
}

# ============================================================
# Main
# ============================================================

$iExitCode = 0

try {
    $sApp = Split-Path -Leaf $sRepoPath

    Write-Host "=== release.ps1 (HomerDev edition, 2026-09-26) ==="
    Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Host "Log:     $sLogPath"
    Write-Host "Repo:    $sRepoPath"
    Write-Host "App:     $sApp  (from the directory name)"
    Write-Host ""

    # --- Tool checks ---
    Write-Host "--- Tool checks ---"
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "git is not in PATH." }
    Write-Host "git: $(& git --version | Select-Object -First 1)"

    $iCode = tryInvoke -sExe 'git' -aArgs @('rev-parse', '--is-inside-work-tree')
    if ($iCode -ne 0) { throw "$sRepoPath is not a git working tree." }

    if ($true) {
        if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
            throw "gh is not in PATH. Install GitHub CLI from https://cli.github.com/ and run: gh auth login"
        }
        $sGhFirstLine = ((& gh --version 2>&1 | Out-String) -split "`n")[0].Trim()
        Write-Host "gh:  $sGhFirstLine"
        $iAuthCode = tryInvoke -sExe 'gh' -aArgs @('auth', 'status')
        if ($iAuthCode -ne 0) {
            & gh auth status
            throw "gh is not authenticated. Run: gh auth login --web --git-protocol https"
        }
        Write-Host "gh authentication: OK"
    }

    # --- Discovery ---
    Write-Host ""
    Write-Host "--- Discovery ---"
    $sIssPath = getIssPath -sPath $sRepoPath -sApp $sApp
    $bHasInstaller = [bool] $sIssPath
    $sIssName = ''
    $sSetupExe = ''
    if ($bHasInstaller) {
        $sIssName = Split-Path -Leaf $sIssPath
        $aIssLines = [System.IO.File]::ReadAllText($sIssPath) -split "`r?`n"
        Write-Host "Setup script: $sIssName"

        # Asset name comes from OutputBaseFilename so it always matches what Inno
        # actually emits. F11 downloads this exact name and GitHub is case-sensitive.
        $sBase = getIssDirective -aLines $aIssLines -sName 'OutputBaseFilename'
        if (-not $sBase) { $sBase = "$($sApp)_setup" }
        $sSetupExe = "$sBase.exe"
        Write-Host "Installer:    $sSetupExe  (from OutputBaseFilename)"
    } else {
        Write-Host "Setup script: none. $sApp ships source, so the release carries no installer."
    }

    $sOwnerRepo = getOwnerRepo
    Write-Host "GitHub repo:  $sOwnerRepo  (from the origin remote)"

    # --- Version ---
    Write-Host ""
    Write-Host "--- Version ---"
    # The version is taken from the INSTALLER ITSELF -- the version resource that
    # Inno stamped into EdSharp_Setup.exe (etc.) from version.txt when you compiled
    # it.  That file is the thing that actually ships, and its number is the one the
    # installed program will report, so it is the only number that can be tagged
    # truthfully.  Reading a text file instead invites every mismatch we have hit:
    # the file says one thing, the built installer says another, and the release ends
    # up labelled wrong.  The artifact cannot lie about what it contains.
    $sSetupPath = ''
    $sVersion = ''
    if ($bHasInstaller) {
        # The top of the project is where every Homer build writes it. exec is
        # where some apps wrote it before: DbDo until 26 September 2026, when a
        # release that looked only at the top stopped with "not found".
        $sSetupPath = Join-Path $sRepoPath $sSetupExe
        if (-not (Test-Path -LiteralPath $sSetupPath -PathType Leaf)) {
            $sInExec = Join-Path (Join-Path $sRepoPath 'exec') $sSetupExe
            if (Test-Path -LiteralPath $sInExec -PathType Leaf) {
                Write-Host "Installer found in exec rather than at the top of the project; build$sApp should write it at the top (OutputDir=.)." -ForegroundColor Yellow
                $sSetupPath = $sInExec
            } else {
                throw "$sSetupExe was found neither in $sRepoPath nor in its exec folder. Run build$sApp, which builds the installer, then release again."
            }
        }
        $oExe = Get-Item -LiteralPath $sSetupPath
        try { $sVersion = ("" + $oExe.VersionInfo.FileVersion).Trim() } catch { }
        if (-not $sVersion) {
            throw "$sSetupExe carries no version resource. Check that $sIssName sets VersionInfoVersion."
        }
        Write-Host "Version (stamped in $sSetupExe): $sVersion"
        Write-Host ("  built: {0}   {1:N0} bytes" -f $oExe.LastWriteTime, $oExe.Length)
    } else {
        # No installer, so there is no artifact to read a version out of, and
        # version.txt becomes the source of truth rather than a cross-check.
        $sVerOnly = Join-Path $sRepoPath "version.txt"
        if ($Version) {
            $sVersion = $Version.Trim()
            Write-Host "Version (given with -Version): $sVersion"
        } elseif (Test-Path -LiteralPath $sVerOnly -PathType Leaf) {
            $sVersion = ((Get-Content -LiteralPath $sVerOnly -TotalCount 1) + "").Trim()
            Write-Host "Version (from version.txt): $sVersion"
        }
        if (-not $sVersion) {
            throw "No version to release. $sApp has no installer, so put the version in version.txt or pass -Version."
        }
    }

    # version.txt should agree.  If it does not, the installer was compiled from a
    # different version than the build last assigned -- say so, but tag what actually
    # ships, which is the installer.
    $sVerPath = Join-Path $sRepoPath "version.txt"
    if ($bHasInstaller -and (Test-Path -LiteralPath $sVerPath -PathType Leaf)) {
        $sFileVersion = ((Get-Content -LiteralPath $sVerPath -TotalCount 1) + "").Trim()
        if ($sFileVersion -and -not (sameVersion $sFileVersion $sVersion)) {
            $bOlder = $false
            try { $bOlder = ([version] $sVersion) -lt ([version] $sFileVersion) } catch { }
            if ($bOlder -and -not $Force) {
                throw ("The installer carries $sVersion, but version.txt says ${sFileVersion}: the last build " +
                       "stepped the version without finishing a new installer, so $sSetupExe is an older " +
                       "build. Run build$sApp, then release again. (release -Force publishes the older " +
                       "installer anyway.)")
            }
            Write-Host "NOTE: version.txt says $sFileVersion but the installer carries $sVersion." -ForegroundColor Yellow
            Write-Host "      The installer is what ships, so v$sVersion is what will be tagged." -ForegroundColor Yellow
        }
    }

    # --- The project's own check ---
    # A release should pass the checks its project wrote for itself: accept.inix
    # and the kit's documents, encoding, whitelist, naming and keys checks.
    $sCheck = Join-Path (Join-Path $sRepoPath 'scripts') 'check.cmd'
    if (-not $NoCheck -and (Test-Path -LiteralPath $sCheck -PathType Leaf)) {
        Write-Host ""
        Write-Host "--- Check ---"
        Write-Host "  > scripts\check" -ForegroundColor DarkGray
        $oCheck = runNative -sExe $sCheck
        if ($oCheck.Out) { Write-Host $oCheck.Out }
        if ($oCheck.Code -ne 0) {
            throw "scripts\check found a problem, so nothing was published. Its report in logs names it. (release -NoCheck skips the check.)"
        }
        Write-Host "The check passed."
    }

    if (-not $SkipStaleCheck -and (isReleased -sTag "v$sVersion")) {
        Write-Host ""
        Write-Host "=== ALREADY RELEASED -- nothing was published. ===" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "The installer on disk carries v$sVersion, which is already on GitHub." -ForegroundColor Yellow
        Write-Host "So this is the same build that was released before -- there is nothing new." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "build$sApp takes a NEW version every time it runs.  So:" -ForegroundColor Yellow
        Write-Host ""
        if ($bHasInstaller) {
            Write-Host "  1. build$sApp        (steps the version and builds a new installer)" -ForegroundColor Yellow
            Write-Host '  2. scripts\push "What changed."' -ForegroundColor Yellow
            Write-Host "  3. scripts\release" -ForegroundColor Yellow
        } else {
            Write-Host "  1. Raise the number in version.txt, or pass -Version" -ForegroundColor Yellow
            Write-Host "  2. git add -A  /  git commit  /  git push" -ForegroundColor Yellow
            Write-Host "  3. release" -ForegroundColor Yellow
        }
        Write-Host ""
        Stop-Transcript | Out-Null
        exit 0
    }
    Write-Host "v$sVersion has not been released yet."
    $sTag = "v$sVersion"
    Write-Host "Tag:       $sTag"

    # Nothing to sync.  The version lives only in the .iss, and the build already
    # compiled it into the program (Version.cs) and the installer (Inno).  This
    # script does not write to any source file.
    $aChangedFiles = @()

    # No separate "asset check" is needed any more.  The installer was located and
    # its version read above -- that IS the version being tagged, so the two cannot
    # disagree.  The old check existed only because the version came from elsewhere.

    # --- Commit the version files ---
    # Uncommitted changes never block the release. The version files that this
    # script edited are committed so the tag points at a commit that actually
    # contains this version; anything else outstanding is reported and left alone.
    Write-Host ""
    Write-Host "--- Working tree ---"
    if ($aChangedFiles.Count -gt 0 -and -not $NoCommit) {
        Write-Host "Committing version files: $($aChangedFiles -join ', ')"
        invokeChecked -sExe 'git' -aArgs (@('add') + $aChangedFiles)
        invokeChecked -sExe 'git' -aArgs @('commit', '-m', "$sApp $sVersion")
        $iCode = tryInvoke -sExe 'git' -aArgs @('push')
        if ($iCode -ne 0) { Write-Host "WARN: could not push the version commit; the tag will still be pushed." -ForegroundColor Yellow }
    }
    $sStatus = readQuiet -sExe 'git' -aArgs @('status', '--porcelain')
    if ($sStatus) {
        Write-Host "NOTE: other uncommitted changes are present. Releasing anyway:" -ForegroundColor Yellow
        Write-Host $sStatus -ForegroundColor Yellow
    } else {
        Write-Host "Working tree is clean."
    }

    # --- Tag ---
    Write-Host ""
    Write-Host "--- Tag ---"
    $iCode = tryInvoke -sExe 'git' -aArgs @('rev-parse', $sTag)
    if ($iCode -ne 0) {
        Write-Host "Creating tag $sTag ..."
        invokeChecked -sExe 'git' -aArgs @('tag', '-a', $sTag, '-m', "$sApp $sVersion")
        Write-Host "Pushing tag $sTag to origin ..."
        invokeChecked -sExe 'git' -aArgs @('push', 'origin', $sTag)
    } else {
        Write-Host "Tag $sTag already exists locally. Ensuring it is pushed ..."
        [void] (invokeQuiet -sExe 'git' -aArgs @('push', 'origin', $sTag))
    }

    # --- Release ---
    Write-Host ""
    Write-Host "--- Release ---"
    $iCode = tryInvoke -sExe 'gh' -aArgs @('release', 'view', $sTag)
    if ($iCode -ne 0) {
        if ($bHasInstaller) {
            Write-Host "Creating release $sTag with asset $sSetupExe ..."
            invokeChecked -sExe 'gh' -aArgs @(
                'release', 'create', $sTag, $sSetupPath,
                '--title', "$sApp $sVersion",
                '--generate-notes',
                '--latest'
            )
        } else {
            Write-Host "Creating release $sTag (source only, no asset) ..."
            invokeChecked -sExe 'gh' -aArgs @(
                'release', 'create', $sTag,
                '--title', "$sApp $sVersion",
                '--generate-notes',
                '--latest'
            )
        }
    } else {
        if ($bHasInstaller) {
            Write-Host "Release $sTag already exists. Replacing asset and marking it latest ..."
            invokeChecked -sExe 'gh' -aArgs @('release', 'upload', $sTag, $sSetupPath, '--clobber')
        } else {
            Write-Host "Release $sTag already exists. Marking it latest ..."
        }
        # A RELEASE THAT EXISTS MAY BE A DRAFT (1.43.15). EdSharp's v5.0.15 was
        # one, left by an earlier run: invisible to the public, so the list of
        # releases rightly said "not released", and "gh release view" found it.
        # Uploading to a draft and marking it latest publishes nothing. It is
        # published here, and a failure says so rather than passing quietly.
        invokeChecked -sExe 'gh' -aArgs @('release', 'edit', $sTag, '--draft=false', '--latest')
    }

    # --- Verify the public URL ---
    Write-Host ""
    Write-Host "--- URL verification ---"
    if (-not $bHasInstaller) {
        $sUrl = "https://github.com/$sOwnerRepo/releases/tag/$sTag"
        Write-Host "Release page: $sUrl"
        Write-Host ""
        Write-Host "=== $sApp $sVersion published (source only). ===" -ForegroundColor Green
        Write-Host ""
        Stop-Transcript | Out-Null
        exit 0
    }
    # THE LATEST RELEASE MUST BE THIS ONE. The download link below always
    # answers while any earlier release carries an installer of the same name,
    # so its answer alone cannot show that this release went out. GitHub is
    # asked which release it calls latest.
    $oLatest = runNative -sExe 'gh' -aArgs @('api', "repos/$sOwnerRepo/releases/latest", '--jq', '.tag_name')
    $sLatestTag = ("" + $oLatest.Out).Trim()
    if ($oLatest.Code -eq 0 -and $sLatestTag -ne '' -and $sLatestTag -ne $sTag) {
        throw "GitHub's latest release is $sLatestTag, not ${sTag}: $sTag is on GitHub but not the one people download. Its page says why -- a draft, or a pre-release."
    }
    if ($sLatestTag -eq $sTag) { Write-Host "GitHub's latest release: $sLatestTag" }
    $sUrl = "https://github.com/$sOwnerRepo/releases/latest/download/$sSetupExe"
    Write-Host "Public URL: $sUrl"
    try {
        $oResponse = Invoke-WebRequest -Uri $sUrl -Method Head -MaximumRedirection 5 -UseBasicParsing -ErrorAction Stop
        Write-Host ("URL check: HTTP {0}" -f $oResponse.StatusCode) -ForegroundColor Green
    } catch {
        try {
            $oResponse = Invoke-WebRequest -Uri $sUrl -Method Get -MaximumRedirection 5 -UseBasicParsing -ErrorAction Stop
            Write-Host ("URL check: HTTP {0} (via GET; HEAD was rejected)" -f $oResponse.StatusCode) -ForegroundColor Green
        } catch {
            Write-Host "URL check failed: $($_.Exception.Message)" -ForegroundColor Yellow
            Write-Host "(The release may still be valid; GitHub's CDN can take a few seconds to propagate.)" -ForegroundColor Yellow
        }
    }

    Write-Host ""
    Write-Host "=== $sApp $sVersion published. ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Stable public download URL (does not change between versions):"
    Write-Host ""
    Write-Host "  $sUrl"
    Write-Host ""
    Write-Host "Users on an older version will now see this release from Elevate Version (F11)."
    Write-Host ""

} catch {
    $iExitCode = 1
    Write-Host ""
    Write-Host "=== FAILED ===" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ScriptStackTrace) {
        Write-Host ""
        Write-Host "Stack trace:" -ForegroundColor DarkGray
        Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray
    }
} finally {
    Write-Host ""
    Write-Host "--- Log saved at: $sLogPath ---"
    if ($iExitCode -ne 0) { Write-Host "--- Exit code: $iExitCode ---" }
    try { Stop-Transcript | Out-Null } catch { }
}

exit $iExitCode
