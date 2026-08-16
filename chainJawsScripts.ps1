# chainJawsScripts.ps1 -- make the installed HomerView scripts reachable
#
# Compiling HomerView.jsb into the JAWS settings folder does not make JAWS run
# it. JAWS loads the script file NAMED AFTER THE EXECUTABLE, plus the default
# file, and nothing else. Nothing on this machine is called HomerView.exe, so
# HomerView.jsb has been sitting there being loaded by nobody. That is why
# Alt+JAWSKey+H did nothing, and why the other five would have done nothing
# either.
#
# There are two halves to fixing it, and this does both.
#
# THE SCRIPTS. Freedom Scientific's own extension point for adding scripts
# globally is MyExtensions: the default script file calls down to
# MyExtensions.jsb, so a MyExtensions.jss in the USER settings folder that says
# Use "HomerView.jsb" makes every HomerView script available everywhere,
# without a user copy of default.jss existing at all. That last part matters. A
# user default.jss shadows the factory one, which is JAWS's entire interface to
# Windows, and getting it wrong is the failure that needs Narrator started to
# recover from. MyExtensions asks for none of that risk. The one rule is that
# names must be unique, because the default scripts do not call down to
# MyExtensions for a name they already have.
#
# THE KEYS. Key maps are plain text and are layered, application over default.
# The supported way to add a default binding is a user copy of default.jkm, and
# the important word is COPY: this takes the factory file first and adds to it,
# so nothing is lost whether JAWS merges the two or uses only ours. Freedom
# Scientific's own instructions for changing a modifier key say to do exactly
# that. Creating a user default.jkm that holds only our line is the thing to
# avoid, and it is what this project rightly refused to do before.
#
# ALMOST everything goes in default.jkm. [Virtual Keys] there scopes a command
# to "while the virtual cursor is active", which is the right scope for reading
# a page, and only launching sits in [Common Keys], because before HomerView
# runs there is no browser to be in.
#
# THE ONE EXCEPTION IS msedge.jkm, and it is not a shortcut either. A command
# like Open Document should work whenever the BROWSER is in front -- address
# bar, form field, focus mode -- which is a scope [Virtual Keys] cannot express
# and [Common Keys] over-expresses, since that would take Control+O from every
# application on the machine. An application key map says exactly the intended
# thing: this key, in this program, in any cursor mode.
#
# Everything it changes is backed up first, everything it does is recorded in a
# manifest beside the scripts, and -bUndo puts it all back.
#
# Writes chainJawsScripts.log beside itself.

param(
    [switch] $bUndo,
    # Handed over by installJawsScripts so both write to the same file. Run by
    # hand it picks its own, named the same way.
    [string] $pathLogFile = ""
)

$ErrorActionPreference = "Continue"

$pathRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
# The same file the installer is writing, when it says so. Run on its own it
# starts one of its own, named the same way.
$pathLog = $pathLogFile
if (-not $pathLog) {
    $pathLog = Join-Path $env:LOCALAPPDATA ("HomerView\logs\HomerViewJAWS{0:yyyyMMdd-HHmmss}.log" -f (Get-Date))
}
try { New-Item -ItemType Directory -Force -Path (Split-Path $pathLog) | Out-Null } catch { }

# The comment that marks our own lines in somebody else's file. Anything
# between this and the end of our block is ours to remove and nothing else is.
$c_sMarker = "; Added by HomerView"

function writeLog {
    param([string] $sMessage)
    $sStamped = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $sMessage
    Write-Host $sStamped
    try { Add-Content -Path $pathLog -Value $sStamped -Encoding UTF8 } catch { }
}

try { Add-Content -Path $pathLog -Value "" -Encoding UTF8 } catch {
    Write-Host "The log could not be started at $pathLog : $($_.Exception.Message)"
}

# Adds lines inside a named section of an ini-style file, rather than at the
# end of it. A key map is sectioned, so a line appended to the bottom lands in
# whichever section happens to be last and is never read as a common key.
function addToSection {
    param([string] $pathFile, [string] $sSection, [string[]] $lNewLines)

    $lLines = @(Get-Content $pathFile)
    $iSection = -1
    for ($i = 0; $i -lt $lLines.Count; $i++) {
        if ($lLines[$i].Trim() -eq $sSection) { $iSection = $i; break }
    }
    # ANY OTHER BINDING FOR A KEY WE TAKE IS REMOVED FIRST.
    #
    # JAWSKey+L was written into [Common Keys], read back correctly, and still
    # did nothing when pressed. A key map that binds one key twice does not
    # error; one of them simply wins, and which one is not something to guess
    # at from outside. Our line is the one the user asked for, so anything else
    # binding the same key goes -- and is LOGGED, because taking a binding away
    # from somebody silently is worse than the fault it fixes.
    $lTake = @()
    foreach ($sNew in $lNewLines) { $lTake += ($sNew -split "=")[0].Trim().ToLower() }
    $lKept = @()
    foreach ($sLine in $lLines) {
        $sKey = ($sLine -split "=")[0].Trim().ToLower()
        if ($sLine -notmatch "=" -or $sLine.Trim().StartsWith(";")) { $lKept += $sLine; continue }
        if ($lTake -contains $sKey) {
            writeLog "      displaced an existing binding: $($sLine.Trim())"
            continue
        }
        $lKept += $sLine
    }
    $lLines = $lKept
    $iSection = -1
    for ($i = 0; $i -lt $lLines.Count; $i++) {
        if ($lLines[$i].Trim() -eq $sSection) { $iSection = $i; break }
    }

    $lBlock = @($c_sMarker) + $lNewLines + @("$c_sMarker ends")
    if ($iSection -lt 0) {
        writeLog "      the file has no $sSection section, so one is added"
        $lOut = $lLines + @("", $sSection) + $lBlock
    } else {
        $lOut = @()
        if ($iSection -gt 0) { $lOut += $lLines[0..$iSection] } else { $lOut += $lLines[0] }
        $lOut += $lBlock
        if ($iSection -lt ($lLines.Count - 1)) { $lOut += $lLines[($iSection + 1)..($lLines.Count - 1)] }
    }
    Set-Content -Path $pathFile -Value $lOut -Encoding UTF8
}

# Takes our block back out, leaving whatever was there before it untouched.
function removeOurBlock {
    param([string] $pathFile)

    $lLines = @(Get-Content $pathFile)
    $lOut = @()
    $bInside = $false
    $iRemoved = 0
    foreach ($sLine in $lLines) {
        if ($sLine.Trim() -eq $c_sMarker) { $bInside = $true; $iRemoved += 1; continue }
        if ($sLine.Trim() -eq "$c_sMarker ends") { $bInside = $false; $iRemoved += 1; continue }
        if ($bInside) { $iRemoved += 1; continue }
        $lOut += $sLine
    }
    if ($iRemoved -gt 0) {
        Set-Content -Path $pathFile -Value $lOut -Encoding UTF8
    }
    return $iRemoved
}

function findSharedSettings {
    param([string] $sVersion, [string] $sLanguage)

    # Where "Explore Shared Settings" goes. Looked for rather than assumed,
    # because a wrong guess here would mean creating a user key map from
    # nothing, which is the one outcome this whole script exists to avoid.
    # The registry first, which is how EdSharp's own script installer does it:
    # HKLM\Software\Freedom Scientific\JAWS\<version>\Target is the program
    # folder, and the factory Settings tree sits inside it. Two runs looked in
    # ProgramData, found a Settings\enu folder that was real and empty of
    # everything that matters, and wrote fresh files instead of adding to the
    # factory ones.
    $sTarget = ""
    try {
        $sTarget = (Get-ItemProperty -Path "HKLM:\Software\Freedom Scientific\JAWS\$sVersion" -Name "Target" -ErrorAction Stop).Target
    } catch {
    }
    if ($sTarget) {
        writeLog "    registry Target for JAWS $sVersion : $sTarget"
    } else {
        writeLog "    registry Target for JAWS $sVersion could not be read"
    }
    $lCandidates = @()
    if ($sTarget) {
        $lCandidates += (Join-Path $sTarget "Settings\$sLanguage")
        $lCandidates += (Join-Path $sTarget "Settings")
    }
    $lCandidates += @(
        (Join-Path $env:ProgramData "Freedom Scientific\JAWS\$sVersion\Settings\$sLanguage"),
        (Join-Path ${env:ProgramFiles} "Freedom Scientific\JAWS\$sVersion\Settings\$sLanguage"),
        (Join-Path ${env:ProgramFiles(x86)} "Freedom Scientific\JAWS\$sVersion\Settings\$sLanguage"),
        (Join-Path $env:ProgramData "Freedom Scientific\JAWS\$sVersion\Settings"),
        (Join-Path ${env:ProgramFiles} "Freedom Scientific\JAWS\$sVersion\Settings"),
        (Join-Path ${env:ProgramFiles(x86)} "Freedom Scientific\JAWS\$sVersion\Settings")
    )
    # Every candidate is reported with what was found in it, because two runs
    # have now ended with an empty shared inventory and no way to tell whether
    # the folder was wrong or genuinely bare.
    foreach ($sCandidate in $lCandidates) {
        if (Test-Path $sCandidate) {
            $bHas = Test-Path (Join-Path $sCandidate "default.jkm")
            writeLog "    candidate: $sCandidate -- default.jkm $(if ($bHas) { 'IS' } else { 'is NOT' }) here"
        }
    }
    # The folder that HAS the factory files, not merely the first that exists.
    #
    # Taking the first that existed found C:\ProgramData\...\Settings\enu, which
    # is real and holds none of them, so the inventory came back empty, the
    # factory MyExtensions.jss was never copied, and a fresh one was written
    # over the top of it. Checking that a folder is there is not checking that
    # it is the right folder.
    foreach ($sCandidate in $lCandidates) {
        if (Test-Path (Join-Path $sCandidate "default.jkm")) { return $sCandidate }
    }
    # Nothing had default.jkm in it, so report whichever exists and let the log
    # say plainly that the factory files were not found.
    foreach ($sCandidate in $lCandidates) {
        if (Test-Path $sCandidate) { return $sCandidate }
    }
    return ""
}

function compileFile {
    param([string] $sCompiler, [string] $pathJss)

    $sBase = [System.IO.Path]::GetFileNameWithoutExtension($pathJss)
    $pathJsb = Join-Path (Split-Path -Parent $pathJss) "$sBase.jsb"
    writeLog "      compiling $sBase.jss"
    $sOutput = & $sCompiler $pathJss 2>&1 | Out-String
    foreach ($sLine in ($sOutput -split "`n")) {
        if ($sLine.Trim()) { writeLog "        $($sLine.Trim())" }
    }
    if ($sOutput -match '(?m)^.*\bError:') {
        writeLog "      ERROR: the compiler rejected $sBase.jss. The lines above say where."
        return $false
    }
    if (-not (Test-Path $pathJsb)) {
        writeLog "      ERROR: no $sBase.jsb was produced."
        return $false
    }
    $iSize = (Get-Item $pathJsb).Length
    if ($iSize -lt 100) {
        writeLog "      ERROR: $sBase.jsb is only $iSize bytes, which is too small to be a build."
        return $false
    }
    writeLog "      compiled $sBase.jsb ($iSize bytes)"
    return $true
}

writeLog "chainJawsScripts starting"
writeLog "  script:            $($MyInvocation.MyCommand.Path)"
writeLog "  PowerShell:        $($PSVersionTable.PSVersion)"
writeLog "  platform:          $([System.Environment]::OSVersion.VersionString)"
writeLog "  running as:        $env:USERNAME"
writeLog "  roaming data:      $env:APPDATA"
writeLog "  program data:      $env:ProgramData"
writeLog "  undoing:           $bUndo"
writeLog ""

$pathJawsRoot = Join-Path $env:APPDATA "Freedom Scientific\JAWS"
if (-not (Test-Path $pathJawsRoot)) {
    writeLog "JAWS is not installed for this user, so there is nothing to do."
    exit 0
}
$lVersions = @(Get-ChildItem -Path $pathJawsRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^\d{4}(\.\d+)?$' })
if ($lVersions.Count -eq 0) {
    writeLog "No JAWS version folders were found under $pathJawsRoot."
    exit 0
}
writeLog "JAWS versions found: $(($lVersions | ForEach-Object { $_.Name }) -join ', ')"
writeLog ""

# The launch command works from anywhere, because before HomerView runs there
# is no browser window to be in. The rest are browser commands and are bound in
# the browser's own key map.
$lCommonKeys = @(
    "Alt+JAWSKey+A=checkAccessibility",
    "Alt+JAWSKey+C=findContacts",
    "Alt+JAWSKey+D=dismissDialog",
    "Alt+JAWSKey+F10=showHomerViewMenu",
    "Alt+JAWSKey+H=launchHomerView",
    "Alt+JAWSKey+I=checkAccessibilityIbm",
    "Alt+Shift+H=showHotkeySummary",
    "Alt+JAWSKey+L=copyLogToClipboard"
)

# WHAT EDGE'S SETTINGS ARE ACTUALLY CALLED, discovered rather than assumed.
#
# I assumed "msedge" and was wrong, and the evidence was in this script's own
# log all along: it probes for default, MyExtensions and msedge files and
# reported NOTHING for msedge, in either settings folder. A key map named
# msedge.jkm sits where JAWS never looks.
#
# JAWS+Q in the browser says what is really going on:
#
#   "Microsoft Edge with Chromium settings are used in the msedge.dll
#    application. The configuration name is wikipedia."
#
# Two facts there. THE APPLICATION IS msedge.DLL, not the exe. And its
# SETTINGS ALIAS is "Microsoft Edge with Chromium" -- that is the base name
# JAWS loads configuration files under, exactly as Appendix D describes for
# Internet Explorer: take the executable name, look it up in ConfigNames.ini,
# and load every file beginning with the alias found there.
#
# ("wikipedia" is a third layer again: JAWS 17 and later load a DOMAIN script
# set on top of the application's when a matching site is open. Not something
# to write to, but worth knowing it is there, because a domain key map would
# take precedence over ours on that site.)
#
# So the alias is looked up rather than hard-coded, because it can differ by
# JAWS version and language. ConfigNames.ini first, in the user folder then
# the shared one; then any existing Edge key map in either folder; and only
# then the name JAWS reported here, as a last resort.
function browserConfigName {
    param([string] $pathUser, [string] $pathShared)
    foreach ($pathWhere in @($pathUser, $pathShared)) {
        if (-not $pathWhere) { continue }
        $pathIni = Join-Path $pathWhere "ConfigNames.ini"
        if (-not (Test-Path $pathIni)) { continue }
        foreach ($sLine in (Get-Content $pathIni)) {
            if ($sLine -match '^\s*msedge\s*=\s*(.+?)\s*$') {
                writeLog "    ConfigNames.ini in $pathWhere says msedge is '$($Matches[1])'"
                return $Matches[1]
            }
        }
    }
    foreach ($pathWhere in @($pathUser, $pathShared)) {
        if (-not $pathWhere) { continue }
        $oFound = Get-ChildItem -Path $pathWhere -Filter "*Edge*.jkm" -File -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($oFound) {
            $sName = [System.IO.Path]::GetFileNameWithoutExtension($oFound.Name)
            writeLog "    found an existing Edge key map, so the settings name is '$sName'"
            return $sName
        }
    }
    writeLog "    no Edge settings name could be discovered; using the name JAWS reported"
    return "Microsoft Edge with Chromium"
}


# KEYS SCOPED TO THE BROWSER, IN ANY CURSOR MODE.
#
# A key map has a section per cursor context, so [Virtual Keys] in default.jkm
# means "only while the virtual cursor is active" -- which is NOT the same as
# "while the browser is in front". Control+O in the address bar, in a form
# field, or in focus mode fell through to whatever else wanted it, and once
# fell all the way through to Adobe Reader.
#
# [Common Keys] in default.jkm would fix the mode and break the scope: JAWS
# would intercept Control+O in EVERY application and have to hand it back by
# hand, which is the global hotkey he explicitly does not want.
#
# WHICH COMMANDS BELONG HERE, AND WHICH STAY IN [Virtual Keys]:
#
#   A command that acts on the PAGE, the WINDOW or the PROGRAM belongs here.
#   Saving the page, listing its names, downloading its files, opening a
#   document or a guide, naming the tabs -- none of these depend on where the
#   cursor is, and all of them are things to want while typing in a form or
#   standing in the address bar.
#
#   A command that acts AT THE CURSOR stays in [Virtual Keys], because outside
#   the virtual cursor there IS no cursor for it to act at. Start and Complete
#   Selection, Copy Line, Link Target, Jump to Probable Main and the whole find
#   family are meaningless in a form field, and Control+C especially must go on
#   meaning copy there.
#
#   The clipboard family stays virtual too. It is not cursor-bound, but it
#   belongs to the reading workflow, and an apostrophe combination is a poorer
#   thing to intercept while somebody is typing.
#
# AN APPLICATION KEY MAP IS THE MECHANISM THAT MEANS WHAT HE ASKED FOR. Keys in
# msedge.jkm apply when Edge is the active application and nowhere else, and
# [Common Keys] WITHIN THAT FILE means every cursor mode within it. Word keeps
# its own Control+O and never sees ours.
$lBrowserKeys = @(
    # EMPTY, AND NOW FOR A REASON I CAN CITE RATHER THAN GUESS.
    #
    # Freedom Scientific's own script manual, 3.2 Processing Keystrokes, gives
    # the algorithm exactly:
    #
    #   JAWS first looks for the keystroke in the APPLICATION key map. If it
    #   finds it there, it notes the script name and then looks for that
    #   script IN THE APPLICATION SCRIPT FILE.
    #
    #   Only if the keystroke is NOT in the application key map does it search
    #   the default key map -- and a script named there is looked for in the
    #   application script file first, then in the default file.
    #
    # HomerView's scripts live in MyExtensions, which belongs to the DEFAULT
    # chain, not to Edge's script file. So a key in Edge's key map names a
    # script Edge's script file does not contain.
    #
    # AND 2.8 Keyboard Manager Options MAKES IT WORSE, WHICH IS WHY THIS IS
    # EMPTY RATHER THAN LEFT AS A TEST: "If a keystroke is assigned in both the
    # application and default key map files, ONLY THE APPLICATION KEYSTROKE IS
    # ACTIVE. JAWS always acts on the first keystroke it finds and it looks in
    # the application key map file first."
    #
    # So the fallback I thought I had was not one. Putting Control+O in Edge's
    # map would have SHADOWED the working [Virtual Keys] binding and could have
    # broken the one command he most wants, in the one mode where it works
    # today.
    #
    # THE ROUTE THAT MAKES THIS WORK is to put HomerView's scripts INTO Edge's
    # script set -- Doug Lee's .chain, or the Merge technique from his own
    # HomerKit: a user copy of Edge's script file with Use "HomerView.jsb"
    # added, recompiled. Then the application script file DOES contain
    # openDocument and the application key map resolves. That is the next
    # piece of work and it is worth doing carefully.
)
# Shift+Q IS taken, at his decision: a page has one main region, so the native
# meaning of Shift+Q -- the PREVIOUS one -- has nowhere to go. Every letter is
# already a navigation quick key, and Shift with a
# quick key is reserved for the previous element of that kind.
# The screen reader modifier is deliberately absent here, and present in the
# common keys above. A command that only means anything on a web page can
# afford the browser's own modifier; launching, the menu and the log have to
# work when the browser has not started, or has started wrongly, which is
# exactly when they are wanted.
# Control+F1 is here rather than in the common keys, though the NVDA side has
# it everywhere: Control+F1 collapses the ribbon in Office, and a guide is not
# worth taking that. It is on the Alternate Menu, which works anywhere.
$lVirtualKeys = @(
    "Alt+Control+F1=openSessionLog",
    "Alt+F1=showAbout",
    "Alt+M=sayMetadata",
    "Alt+N=listNames",
    "Alt+Shift+F1=openQuickStart",
    "Alt+Shift+P=copyPageLinks",
    "Alt+Shift+W=downloadFiles",
    "Alt+Shift+F=openPageFolder",
    "Control+F1=openUserGuide",
    "Control+F8=copyAll",
    "Control+O=openDocument",
    "Control+S=savePage",
    "Control+Shift+E=extractByPattern",
    "Control+Shift+F1=openDeveloperNotes",
    "Shift+F1=showHistory",
    "Shift+F4=sayTabNames",
    "Shift+F9=extractMainContent",
    "Alt+Apostrophe=sayClipboard",
    "Alt+C=copyAppend",
    "Alt+F8=readAll",
    "Alt+L=describeLinkTarget",
    "Alt+Shift+Apostrophe=clearClipboard",
    "Control+Apostrophe=saveClipboard",
    "Control+C=copySelection",
    "F8=startSelection",
    "Shift+F8=completeSelection",
    "Control+Shift+Apostrophe=appendClipboard",
    "Shift+Q=moveToProbableMain",
    "Control+F3=findByPattern",
    "Control+Shift+F=findBackwards",
    "Control+Shift+F3=findByPatternBackwards",
    "F3=findNext",
    "Shift+F3=findPrevious",
)

$iDone = 0
$iSkipped = 0
$iFailed = 0

foreach ($folderVersion in $lVersions) {
    $sVersion = $folderVersion.Name
    writeLog "JAWS $sVersion"

    $lCompilers = @(
        (Join-Path ${env:ProgramFiles} "Freedom Scientific\JAWS\$sVersion\scompile.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Freedom Scientific\JAWS\$sVersion\scompile.exe")
    )
    $sCompiler = $lCompilers | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $sCompiler) {
        writeLog "  scompile.exe for JAWS $sVersion was not found, so this version is skipped."
        writeLog ""
        $iSkipped += 1
        continue
    }

    $lSettings = @(Get-ChildItem -Path (Join-Path $folderVersion.FullName "Settings") -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^[A-Za-z]{3}$' })
    if ($lSettings.Count -eq 0) {
        writeLog "  no settings folder, so skipping this version"
        writeLog ""
        $iSkipped += 1
        continue
    }

    foreach ($folderLanguage in $lSettings) {
        $pathUser = $folderLanguage.FullName
        $sLanguage = $folderLanguage.Name
        $pathShared = findSharedSettings $sVersion $sLanguage
        writeLog "  user settings:   $pathUser"
        if ($pathShared) {
            writeLog "  shared settings: $pathShared"
        } else {
            writeLog "  shared settings: NOT FOUND"
        }

        # What is already there, recorded before anything is changed. This
        # answers on its own the question of whether another script set has
        # been here first, and what the browser's files are really called.
        writeLog "  what is already in place:"
        foreach ($sBase in @("default", "MyExtensions", "msedge", "Microsoft Edge with Chromium")) {
            foreach ($sWhere in @("user", "shared")) {
                $pathWhere = if ($sWhere -eq "user") { $pathUser } else { $pathShared }
                if (-not $pathWhere) { continue }
                $lFound = @(Get-ChildItem -Path $pathWhere -Filter "$sBase.*" -File -ErrorAction SilentlyContinue |
                    Where-Object { $_.Extension -match '^\.(jss|jsb|jkm|jsd)$' } |
                    ForEach-Object { $_.Name })
                if ($lFound.Count -gt 0) {
                    writeLog "    $sWhere : $($lFound -join ', ')"
                }
            }
        }

        $pathManifest = Join-Path $pathUser "homerViewChain.manifest"

        # ---------------------------------------------------------------- undo
        if ($bUndo) {
            if (-not (Test-Path $pathManifest)) {
                writeLog "  nothing was recorded as done here, so there is nothing to undo"
                writeLog ""
                continue
            }
            foreach ($sEntry in (Get-Content $pathManifest)) {
                $lParts = $sEntry -split "\|", 2
                if ($lParts.Count -lt 2) { continue }
                $sAction = $lParts[0]
                $sName = $lParts[1]
                $pathFile = Join-Path $pathUser $sName
                if ($sAction -eq "created") {
                    foreach ($sExtension in @("", ".jsb")) {
                        $pathGone = if ($sExtension) { [System.IO.Path]::ChangeExtension($pathFile, "jsb") } else { $pathFile }
                        if (Test-Path $pathGone) {
                            Remove-Item $pathGone -Force
                            writeLog "    removed $(Split-Path $pathGone -Leaf), which we created"
                        }
                    }
                } elseif ($sAction -eq "edited") {
                    $pathBackup = "$pathFile.homerViewBackup"
                    if (Test-Path $pathBackup) {
                        Copy-Item $pathBackup $pathFile -Force
                        Remove-Item $pathBackup -Force
                        writeLog "    restored $sName from the backup taken before it was changed"
                    } elseif (Test-Path $pathFile) {
                        $iOut = removeOurBlock $pathFile
                        writeLog "    took $iOut of our lines back out of $sName"
                    }
                }
            }
            # MyExtensions may have been edited rather than created, in which
            # case what is now on disk is somebody else's and has to be built
            # again.
            $pathMine = Join-Path $pathUser "MyExtensions.jss"
            if (Test-Path $pathMine) { $null = compileFile $sCompiler $pathMine }
            Remove-Item $pathManifest -Force
            writeLog "  undone. Restart JAWS for it to take effect."
            writeLog ""
            $iDone += 1
            continue
        }

        # ------------------------------------------------------------- install
        $lManifest = @()
        if (Test-Path $pathManifest) {
            writeLog "  this folder has been done already; it is being redone from the manifest"
            $lManifest = @(Get-Content $pathManifest)
        }

        $pathHomerJsb = Join-Path $pathUser "HomerView.jsb"
        if (-not (Test-Path $pathHomerJsb)) {
            writeLog "  ERROR: HomerView.jsb is not here. Run the HomerView installer first,"
            writeLog "         with the JAWS box ticked, then run this again."
            writeLog ""
            $iFailed += 1
            continue
        }

        # --- MyExtensions ------------------------------------------------
        $pathMyJss = Join-Path $pathUser "MyExtensions.jss"
        $pathMyJsb = Join-Path $pathUser "MyExtensions.jsb"
        $bScriptsOk = $false
        if ((Test-Path $pathMyJsb) -and (-not (Test-Path $pathMyJss))) {
            # The same rule the script chaining convention uses: a compiled
            # file with no source means somebody got here first and left no way
            # in. Guessing at its contents would throw away their work.
            writeLog "  ERROR: MyExtensions.jsb is here but MyExtensions.jss is not, so another"
            writeLog "         set of scripts owns it and there is no source to add to."
            $iFailed += 1
        } else {
            if (Test-Path $pathMyJss) {
                $sMy = Get-Content $pathMyJss -Raw
                if ($sMy -match '(?im)^\s*use\s+"HomerView\.jsb"') {
                    writeLog "    MyExtensions.jss already uses HomerView.jsb"
                } else {
                    if (-not (Test-Path "$pathMyJss.homerViewBackup")) {
                        Copy-Item $pathMyJss "$pathMyJss.homerViewBackup" -Force
                        writeLog "    backed up MyExtensions.jss before changing it"
                    }
                    # Below any Use lines that are already there, so an earlier
                    # author keeps whatever order they chose.
                    $lMy = @(Get-Content $pathMyJss)
                    $iLastUse = -1
                    for ($i = 0; $i -lt $lMy.Count; $i++) {
                        if ($lMy[$i] -match '(?i)^\s*use\s+"') { $iLastUse = $i }
                    }
                    $lBlock = @($c_sMarker, 'Use "HomerView.jsb"', "$c_sMarker ends")
                    if ($iLastUse -lt 0) {
                        $lMy = $lBlock + $lMy
                    } else {
                        $lMy = $lMy[0..$iLastUse] + $lBlock + $lMy[($iLastUse + 1)..($lMy.Count - 1)]
                    }
                    Set-Content -Path $pathMyJss -Value $lMy -Encoding UTF8
                    writeLog "    added Use HomerView.jsb to MyExtensions.jss"
                    $lManifest += "edited|MyExtensions.jss"
                }
            } else {
                $pathSharedMy = if ($pathShared) { Join-Path $pathShared "MyExtensions.jss" } else { "" }
                if ($pathSharedMy -and (Test-Path $pathSharedMy)) {
                    Copy-Item $pathSharedMy $pathMyJss -Force
                    writeLog "    copied the factory MyExtensions.jss, so nothing in it is lost"
                    $lMy = @(Get-Content $pathMyJss)
                    $iLastUse = -1
                    for ($i = 0; $i -lt $lMy.Count; $i++) {
                        if ($lMy[$i] -match '(?i)^\s*use\s+"') { $iLastUse = $i }
                    }
                    $lBlock = @($c_sMarker, 'Use "HomerView.jsb"', "$c_sMarker ends")
                    if ($iLastUse -lt 0) { $lMy = $lBlock + $lMy } else {
                        $lMy = $lMy[0..$iLastUse] + $lBlock + $lMy[($iLastUse + 1)..($lMy.Count - 1)]
                    }
                    Set-Content -Path $pathMyJss -Value $lMy -Encoding UTF8
                    $lManifest += "created|MyExtensions.jss"
                } else {
                    # Nothing to preserve, so the smallest file that can hold a
                    # Use line. The function is there because a script file of
                    # nothing but Use lines is not reliably accepted.
                    $lNew = @(
                        "; MyExtensions.jss -- where scripts added to JAWS itself belong.",
                        ";",
                        "; The default script file calls down to this one, so anything named here",
                        "; is available in every application without a user copy of default.jss",
                        "; existing at all. Names have to be unique: the default scripts do not",
                        "; call down for a name they already have.",
                        "",
                        $c_sMarker,
                        'Use "HomerView.jsb"',
                        "$c_sMarker ends",
                        "",
                        "void Function homerViewChainFiller ()",
                        "Return",
                        "EndFunction"
                    )
                    Set-Content -Path $pathMyJss -Value $lNew -Encoding UTF8
                    writeLog "    wrote a new MyExtensions.jss that uses HomerView.jsb"
                    $lManifest += "created|MyExtensions.jss"
                }
            }
            $bScriptsOk = compileFile $sCompiler $pathMyJss
            if (-not $bScriptsOk) { $iFailed += 1 }
        }

        # --- the key maps -------------------------------------------------
        if ($bScriptsOk) {
            $sBase = "default"
            $pathUserJkm = Join-Path $pathUser "$sBase.jkm"
            $pathSharedJkm = if ($pathShared) { Join-Path $pathShared "$sBase.jkm" } else { "" }

            # EVERY BLOCK OF OURS COMES OUT ONCE, BEFORE ANY GOES BACK IN.
            #
            # removeOurBlock works on the whole file, not on one section, and it
            # used to be called inside the loop below. So the first pass took
            # out both sections' blocks and put [Common Keys] back, and the
            # second pass took out the [Common Keys] block that had just been
            # written and put [Virtual Keys] back. The file ended with the
            # browser keys and no launch key, every log line said success, and
            # the counts even said so out loud: removed 10, then removed 4.
            if (Test-Path $pathUserJkm) {
                if (-not (Test-Path "$pathUserJkm.homerViewBackup")) {
                    Copy-Item $pathUserJkm "$pathUserJkm.homerViewBackup" -Force
                    writeLog "    backed up $sBase.jkm before changing it"
                }
                $iOld = removeOurBlock $pathUserJkm
                if ($iOld -gt 0) {
                    writeLog "    removed $iOld line(s) written by an earlier release"
                }
            }
            foreach ($sPair in @(@("[Common Keys]", $lCommonKeys), @("[Virtual Keys]", $lVirtualKeys))) {
                $sSectionName = $sPair[0]
                $lKeys = $sPair[1]

                if (Test-Path $pathUserJkm) {
                    addToSection $pathUserJkm $sSectionName $lKeys
                    writeLog "    added $($lKeys.Count) key(s) to $sSectionName in the user $sBase.jkm"
                    $lManifest += "edited|$sBase.jkm"
                } elseif ($pathSharedJkm -and (Test-Path $pathSharedJkm)) {
                    # The copy is the whole point. A user key map can be used
                    # in place of the factory one rather than alongside it, so
                    # a file holding only our keys could cost every binding the
                    # factory file provides. Starting from a copy cannot.
                    Copy-Item $pathSharedJkm $pathUserJkm -Force
                    writeLog "    copied the factory $sBase.jkm into the user folder, so nothing is lost"
                    addToSection $pathUserJkm $sSectionName $lKeys
                    writeLog "    added $($lKeys.Count) key(s) to $sSectionName in it"
                    $lManifest += "created|$sBase.jkm"
                } else {
                    writeLog "    ERROR: no default.jkm was found in either folder, so the keys cannot"
                    writeLog "           be added without inventing one. Nothing was changed."
                    $iFailed += 1
                }
            }
            # --- the browser's own key map ---------------------------------
            #
            # Same discipline as default.jkm: back up before changing, take our
            # old block out before putting a new one in, and if there is no user
            # copy yet, COPY THE FACTORY FILE FIRST rather than writing a file
            # that holds only our keys.
            #
            # If Edge has no factory msedge.jkm at all, one is created holding
            # just [Common Keys] and our line. That is safe here in a way it
            # would not be for default.jkm: an application key map that does not
            # exist takes nothing away, because JAWS falls through to the
            # default map for everything it does not name.
            $sEdgeBase = browserConfigName $pathUser $pathShared
            writeLog "    the browser's settings are called '$sEdgeBase'"
            $pathUserEdgeJkm = Join-Path $pathUser "$sEdgeBase.jkm"
            $pathSharedEdgeJkm = if ($pathShared) { Join-Path $pathShared "$sEdgeBase.jkm" } else { "" }
            if (Test-Path $pathUserEdgeJkm) {
                if (-not (Test-Path "$pathUserEdgeJkm.homerViewBackup")) {
                    Copy-Item $pathUserEdgeJkm "$pathUserEdgeJkm.homerViewBackup" -Force
                    writeLog "    backed up $sEdgeBase.jkm before changing it"
                }
                $iOldEdge = removeOurBlock $pathUserEdgeJkm
                if ($iOldEdge -gt 0) {
                    writeLog "    removed $iOldEdge line(s) from $sEdgeBase.jkm written by an earlier release"
                }
            } elseif ($pathSharedEdgeJkm -and (Test-Path $pathSharedEdgeJkm)) {
                Copy-Item $pathSharedEdgeJkm $pathUserEdgeJkm -Force
                writeLog "    copied the factory $sEdgeBase.jkm into the user folder, so nothing is lost"
                $lManifest += "created|$sEdgeBase.jkm"
            } else {
                Set-Content -Path $pathUserEdgeJkm -Value @("[Common Keys]") -Encoding UTF8
                writeLog "    no factory $sEdgeBase.jkm exists, so a new one was written with only our key"
                $lManifest += "created|$sEdgeBase.jkm"
            }
            addToSection $pathUserEdgeJkm "[Common Keys]" $lBrowserKeys
            writeLog "    added $($lBrowserKeys.Count) key(s) to [Common Keys] in $sEdgeBase.jkm"
            writeLog "      these work whenever Edge is in front, in any cursor mode, and nowhere else"
            if ($lManifest -notcontains "created|$sEdgeBase.jkm") {
                $lManifest += "edited|$sEdgeBase.jkm"
            }
            $sEdgeFinal = Get-Content $pathUserEdgeJkm -Raw
            foreach ($sKey in $lBrowserKeys) {
                if (-not $sEdgeFinal.Contains($sKey)) {
                    writeLog "    ERROR: $sKey is not in $sEdgeBase.jkm after writing it"
                    $iFailed += 1
                }
            }

            # What is in the file now, not what was written to it.
            #
            # Every step in this script reported success while the launch key
            # was being deleted by the next step. A count of lines added is a
            # record of an action; reading the key back is a record of an
            # outcome, and only one of those is worth logging.
            $iMissing = 0
            if (Test-Path $pathUserJkm) {
                $sFinal = Get-Content $pathUserJkm -Raw
                foreach ($sKey in ($lCommonKeys + $lVirtualKeys)) {
                    if (-not $sFinal.Contains($sKey)) {
                        writeLog "    ERROR: $sKey is not in $sBase.jkm after writing it"
                        $iMissing += 1
                    }
                }
                # WHEN IT SAYS SOMETHING IS MISSING, SHOW WHAT IS THERE.
                #
                # It reported all seven common keys missing from a file whose
                # common keys were plainly working, so either the write or the
                # reading of it is wrong and the message alone cannot say which.
                # Printing our own lines out of the file settles it in one run:
                # if they are listed here, the check is at fault; if they are
                # not, the write is.
                if ($iMissing -gt 0) {
                    writeLog "    what is actually in $sBase.jkm, our lines only:"
                    $iShown = 0
                    foreach ($sLine in (Get-Content $pathUserJkm)) {
                        if ($sLine -match '^\s*\[') {
                            writeLog "      $sLine"
                            continue
                        }
                        foreach ($sKey in ($lCommonKeys + $lVirtualKeys)) {
                            $sScript = ($sKey -split "=")[1]
                            if ($sLine -like "*$sScript*") {
                                writeLog "      $sLine"
                                $iShown += 1
                                break
                            }
                        }
                    }
                    writeLog "    $iShown of our lines are in the file"
                }
            } else {
                writeLog "    ERROR: $sBase.jkm is not there at all after writing it"
                $iMissing += 1
            }
            if ($iMissing -gt 0) {
                $iFailed += 1
            } else {
                writeLog "    all $(($lCommonKeys + $lVirtualKeys).Count) keys read back correctly from $sBase.jkm"
                $iDone += 1
            }
        }

        if ($lManifest.Count -gt 0) {
            Set-Content -Path $pathManifest -Value ($lManifest | Select-Object -Unique) -Encoding UTF8
        }
        writeLog ""
    }
}

writeLog "Finished. $iDone folders done, $iSkipped skipped, $iFailed with a problem."
if ($iFailed -gt 0) {
    writeLog "Read the lines above. Nothing that failed was left half done."
    exit 1
}
if (-not $bUndo) {
    writeLog "RESTART JAWS, then try Alt+JAWSKey+H from anywhere, Alt+JAWSKey+F10 for"
    writeLog "the menu, and Alt+Shift+H for every key."
    writeLog "With HomerView's browser focused, Insert+Q says which scripts are loaded."
    writeLog "To put everything back: chainJawsScripts -bUndo"
}
exit 0
