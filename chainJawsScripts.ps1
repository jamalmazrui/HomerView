# chainJawsScripts.ps1 -- bind HomerView's keys inside the browser, and
# nowhere else.
#
# Compiling HomerView.jsb into a JAWS settings folder does not make JAWS run
# it. JAWS loads the script file NAMED AFTER THE EXECUTABLE, plus the default
# file, and nothing else. Nothing on the machine is called HomerView.exe, so
# HomerView.jsb sat there being loaded by nobody.
#
# WHAT THIS WRITES, AND IT IS THE WHOLE LIST: two files named after the
# browser, in the user settings folder.
#
#   <browser>.jss   Uses the factory browser scripts first, when JAWS ships
#                   any, then HomerView.jsb. The documentation calls this
#                   LAYERING: anything not overridden is inherited, so
#                   everything Vispero provides still works.
#   <browser>.jkm   [Common Keys] for the nine that must work in the address
#                   bar and in forms mode, [Virtual Keys] for the thirty-nine
#                   that act on a page. Both sections are inside the browser's
#                   own file, so both are scoped to the browser.
#
# NOTHING OUTSIDE THE BROWSER IS TOUCHED. No user default.jss, no user
# default.jkm, no MyExtensions. That is a change from every release before
# this one, and it is worth saying why each of those went.
#
#   default.jkm held nine keys, and [Virtual Keys] there applies WHEREVER A
#   VIRTUAL CURSOR IS ACTIVE -- an Outlook message, a Word document and a PDF
#   all get one. Control+O in Outlook was running HomerView's Open Document.
#
#   MyExtensions was how the scripts were reached globally, which they no
#   longer need to be, since the browser's own script file Uses HomerView.jsb
#   directly.
#
#   default.jss was read and sometimes rewritten so the chain would reach
#   MyExtensions. That file is JAWS's entire interface to Windows, and getting
#   it wrong is the failure that needs Narrator started to recover from.
#
# THE ONE KEY THAT CANNOT BE SCOPED TO THE BROWSER is the one that starts it.
# That is a Windows shortcut key, Alt+Control+Shift+H, set on a desktop shortcut by
# the installer. It runs HomerView.exe, which reconnects and raises the window
# or starts the browser, so it involves no screen reader at all -- which is
# why the same shortcut serves JAWS and NVDA.
#
# ANY CHROMIUM BROWSER, not only Edge. Which one comes from HomerView.inix, or
# from -sBrowserExe, and JAWS's own ConfigNames.ini says what its script set
# is called. Changing the setting clears the previous browser's files before
# writing the new ones, because two browsers each claiming Control+O is worse
# than either.
#
# Everything it changes is backed up first, everything it does is recorded in
# a manifest beside the scripts, and -bUndo puts it all back.
#
# Writes chainJawsScripts.log beside itself.

param(
    [switch] $bUndo,
    # Handed over by installJawsScripts so both write to the same file. Run by
    # hand it picks its own, named the same way.
    [string] $pathLogFile = "",
    # WHICH BROWSER THE KEYS ARE BOUND IN, as the executable file name --
    # msedge.exe, chrome.exe, brave.exe, vivaldi.exe. Left empty it is read
    # from HomerView.inix, and failing that it is Edge, which is what every
    # installation before this one used.
    #
    # It is a parameter as well as a setting because changing the browser has
    # to rewrite the key maps, and the settings command needs to name the
    # browser it is rewriting them for rather than depend on the file it has
    # just written being read back correctly.
    [string] $sBrowserExe = ""
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


# THE ONE PLACE THE BROWSER IS DECIDED, and it is a file both sides read.
#
# HomerView.inix in the roaming application data folder is where the add-on
# keeps preferences, so the setting lives there rather than in a second store
# of this script's own. A second store is how two halves of one program come
# to disagree about which browser they are driving.
#
# The value wanted is browserPath, a full path to the executable, because that
# is what actually launches. The executable's file name is derived from it,
# because that is what JAWS names a script set after. Deriving one from the
# other means they cannot disagree either.
function chosenBrowserExe {
    param([string] $sGiven)

    if ($sGiven) {
        writeLog "  browser: $sGiven, given on the command line"
        return [System.IO.Path]::GetFileName($sGiven)
    }
    $pathInix = Join-Path $env:APPDATA "HomerView\HomerView.inix"
    if (Test-Path $pathInix) {
        foreach ($sLine in (Get-Content $pathInix -ErrorAction SilentlyContinue)) {
            if ($sLine -match '^\s*browserPath\s*=\s*(.+?)\s*$') {
                $sPath = $Matches[1]
                if ($sPath) {
                    writeLog "  browser: $sPath, from HomerView.inix"
                    return [System.IO.Path]::GetFileName($sPath)
                }
            }
        }
        writeLog "  HomerView.inix is here but names no browser, so Edge is assumed"
    } else {
        writeLog "  no HomerView.inix yet, so Edge is assumed"
    }
    return "msedge.exe"
}

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
    # THE SCREEN READER MODIFIER IS GONE FROM ALL BUT NOTHING, AND ON PURPOSE.
    #
    # These used to be Alt+JAWSKey+letter, which is three keys for a command and
    # a different three on NVDA, where the same command was Alt+NVDA+letter. The
    # modifier was there because these keys used to live in default.jkm and had
    # to be safe in EVERY program on the machine. They live in the browser's own
    # key map now, so the only things they can collide with are the browser, the
    # page, and each other.
    #
    # ALT+SHIFT+LETTER RATHER THAN ALT+LETTER, AND THIS IS THE WHOLE ANALYSIS.
    # Chromium fires an HTML ACCESSKEY on Alt+letter. It does NOT on
    # Alt+Shift+letter. These are [Common Keys], so they fire in the address bar
    # and inside form fields too -- which is exactly where a page's accesskeys
    # are most likely to exist and most likely to be wanted. Alt+Shift keeps the
    # mnemonic letter and takes nothing from the page.
    #
    # WHAT EDGE ITSELF CLAIMS, from Microsoft's current list: Alt alone, Alt+D,
    # Alt+E, Alt+F, Alt+Left, Alt+Right, Alt+Home, Alt+F4, Alt+Shift+B,
    # Alt+Shift+I and Alt+Shift+T. Nothing else with Alt. JAWS, NVDA and Windows
    # claim nothing at all on Alt+letter or Alt+function key.
    #
    # ONE DELIBERATE OVERRIDE: Alt+Shift+B is Edge's "focus the first item in
    # the favorites bar". HomerView's browser runs on a profile of its own with
    # no favorites bar worth focusing, the key is scoped to that window alone,
    # and B is the only mnemonic Choose Browser has. Taken knowingly.
    #
    # TWO CANNOT BE SPELLED, AND WERE RENAMED RATHER THAN GIVEN AN ARBITRARY
    # LETTER. "Check Accessibility with IBM" became "with Equal Access", which
    # is IBM's own name for the engine and what the NVDA side already called it,
    # so E is a real mnemonic. "Diagnostics" became "Report Diagnostics",
    # because D was already Dismiss Dialog's only letter and R is a word in the
    # command rather than a letter picked from the middle of one.
    #
    # ALT+F10 IS THE ONE THAT IS NOT A LETTER, and F10 is the menu key in
    # Windows, which is a stronger association than any letter in "Alternate
    # Menu" would be. Free of Edge, Windows, JAWS, NVDA and HomerView, and a
    # function key can never be an accesskey.
    #
    # LAUNCH KEEPS THREE MODIFIERS ON PURPOSE. Alt+Control+Shift+H is the
    # Windows shortcut key on the desktop icon, so binding the same key here
    # means one key to learn rather than two, and it still works if that icon is
    # ever deleted.
    "Alt+Control+Shift+H=hVLaunchHomerView",
    "Alt+F10=hVShowHomerViewMenu",
    "Alt+Shift+A=hVCheckAccessibility",
    "Alt+Shift+B=hVChooseBrowser",
    "Alt+Shift+C=hVFindContacts",
    "Alt+Shift+D=hVDismissDialog",
    "Alt+Shift+E=hVCheckAccessibilityIbm",
    "Alt+Shift+H=hVHotKeyHelp",
    "Alt+Shift+L=hVCopyLogToClipboard",
    "Alt+Shift+R=hVSayDiagnostics",
    "Alt+Shift+S=hVOpenSettings"
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
    param([string] $pathUser, [string] $pathShared, [string] $sExeBase)

    # WHAT THE BROWSER'S SETTINGS ARE ACTUALLY CALLED, discovered rather than
    # assumed. I assumed "msedge" once and was wrong, and the evidence was in
    # this script's own log all along: it probed for msedge files and reported
    # nothing, in either settings folder. A key map named msedge.jkm sits where
    # JAWS never looks.
    #
    # JAWS+Q in the browser says what is going on:
    #
    #   "Microsoft Edge with Chromium settings are used in the msedge.dll
    #    application. The configuration name is wikipedia."
    #
    # Two facts there. THE APPLICATION IS msedge.DLL, not the exe. And its
    # settings alias is "Microsoft Edge with Chromium" -- the base name JAWS
    # loads configuration files under. The rule, from Appendix D: take the
    # executable name, look it up in ConfigNames.ini, and load every file
    # beginning with the alias found there.
    #
    # ("wikipedia" is a third layer again: JAWS 17 and later load a DOMAIN
    # script set named after the site. Nothing here uses that.)
    #
    # THE LAST RESORT IS THE EXECUTABLE NAME ITSELF, which is what JAWS uses
    # when ConfigNames.ini has no entry -- so it is the documented answer
    # rather than a guess. It is NOT default.jkm. Falling back to the default
    # key map would put the keys in every program with a virtual cursor, which
    # is the whole thing this design exists to stop; better a key map JAWS may
    # not read than a key that fires in Outlook.
    foreach ($pathWhere in @($pathUser, $pathShared)) {
        if (-not $pathWhere) { continue }
        $pathIni = Join-Path $pathWhere "ConfigNames.ini"
        if (-not (Test-Path $pathIni)) { continue }
        foreach ($sLine in (Get-Content $pathIni)) {
            if ($sLine -match "^\s*$([regex]::Escape($sExeBase))\s*=\s*(.+?)\s*$") {
                writeLog "    ConfigNames.ini in $pathWhere says $sExeBase is '$($Matches[1])'"
                return $Matches[1]
            }
        }
    }
    foreach ($pathWhere in @($pathUser, $pathShared)) {
        if (-not $pathWhere) { continue }
        $oFound = Get-ChildItem -Path $pathWhere -Filter "*$sExeBase*.jkm" -File -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($oFound) {
            $sName = [System.IO.Path]::GetFileNameWithoutExtension($oFound.Name)
            writeLog "    found an existing key map, so the settings name is '$sName'"
            return $sName
        }
    }
    writeLog "    ConfigNames.ini has no entry for $sExeBase, so JAWS uses the executable"
    writeLog "    name itself and so do we: '$sExeBase'"
    return $sExeBase
}


# THE PAGE KEYS, WHICH GO IN [Virtual Keys] OF THE BROWSER'S OWN KEY MAP.
#
# Two lists, and the split is by WHEN THE KEY IS SAFE rather than by what the
# command does. [Virtual Keys] applies only while the virtual cursor is
# active, so a plain letter here cannot type itself into a form field or the
# address bar. Shift+Q is taken at his decision: a page has one main region,
# so the native meaning of Shift+Q, the PREVIOUS one, has nowhere to go.
#
# Both lists now live in the browser's key map, so both are scoped to the
# browser. Two empty lists that used to sit here -- one for keys the
# application key map could not resolve, one for keys still in default.jkm --
# are gone with the approach that needed them.
$lPageKeys = @(
    "Alt+Control+F1=hVOpenSessionLog",
    "Alt+F1=hVShowAbout",
    "Alt+M=hVSayMetadata",
    "Alt+N=hVListNames",
    "Alt+Shift+F1=hVOpenQuickStart",
    "Alt+Shift+P=hVCopyPageLinks",
    "Alt+Shift+W=hVDownloadFiles",
    "Alt+R=hVRecentPages",
    "Control+F11=hVElevateVersion",
    "Alt+Shift+F8=hVGoToSelectionStart",
    "Alt+F3=hVFindWordAtCursor",
    "Alt+Shift+F3=hVFindWordAtCursorBackwards",
    "Alt+Shift+F=hVOpenPageFolder",
    "Control+F1=hVOpenUserGuide",
    "Control+F8=hVCopyAll",
    "Control+O=hVOpenDocument",
    "Control+S=hVSavePage",
    "Control+Shift+E=hVExtractByPattern",
    "Control+Shift+Y=hVYieldByPattern",
    "Control+Shift+F1=hVOpenDeveloperNotes",
    "Shift+F1=hVShowHistory",
    "Shift+F4=hVSayTabNames",
    "Shift+F9=hVExtractMainContent",
    "Alt+Apostrophe=hVSayClipboard",
    "Alt+C=hVCopyAppend",
    "Alt+F8=hVReadAll",
    "Alt+L=hVDescribeLinkTarget",
    "Alt+Shift+Apostrophe=hVClearClipboard",
    "Control+Apostrophe=hVSaveClipboard",
    "Control+C=hVCopySelection",
    "F8=hVStartSelection",
    "Shift+F8=hVCompleteSelection",
    "Control+Shift+Apostrophe=hVAppendClipboard",
    "Shift+Q=hVMoveToProbableMain",
    "Control+F3=hVFindByPattern",
    "Control+Shift+F=hVFindBackwards",
    "Control+Shift+F3=hVFindByPatternBackwards",
    "F3=hVFindNext",
    "Shift+F3=hVFindPrevious"
)

$iDone = 0
$iSkipped = 0
$iFailed = 0

# DECIDED ONCE, BEFORE THE LOOP, so every settings folder is set up for the
# same browser. Reading the setting per folder would let a file changed while
# this runs leave two JAWS versions pointing at different browsers.
$sBrowserExe = chosenBrowserExe $sBrowserExe
writeLog ""

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
        foreach ($sBase in @("default", "MyExtensions", "msedge",
                             "Microsoft Edge with Chromium", "chrome",
                             "Google Chrome", "brave", "vivaldi")) {
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
                # A record of WHICH BROWSER this folder was set up for,
                # not a file. It is read on the way in, to clear a
                # previous browser when the setting has changed.
                if ($sAction -eq "browser") { continue }
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
                    # A SOURCE FILE PUT BACK IS STILL THE OLD BINARY UNTIL
                    # IT IS COMPILED. Restoring somebody's .jss and leaving
                    # our .jsb beside it would undo the file and not the
                    # behaviour, which is the worse half to leave done.
                    if ((Test-Path $pathFile) -and $sName -like "*.jss") {
                        $null = compileFile $sCompiler $pathFile
                    }
                }
            }
            # MyExtensions is not written any more, but an installation made
            # by a release that did write it still has to be put back.
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

        # --- THE BROWSER'S OWN SCRIPT SET AND KEY MAP ----------------------
        #
        # THIS IS THE WHOLE OF WHAT HOMERVIEW WRITES INTO A JAWS SETTINGS
        # FOLDER, AND THAT IS THE POINT. Two files named after the browser,
        # plus HomerView.jsb which the installer already put here. No user
        # default.jss, no user default.jkm, no MyExtensions. HomerView changes
        # no default script and no default key map, and that sentence is only
        # worth writing down while it is exactly true.
        #
        # WHAT IT REPLACED, so the reason survives. The keys used to live in
        # default.jkm: nine carrying the JAWS modifier in [Common Keys], and
        # the rest in [Virtual Keys]. [Virtual Keys] there applies WHEREVER A
        # VIRTUAL CURSOR IS ACTIVE, which is not only a browser -- an Outlook
        # message, a Word document and a PDF all get one, and Control+O in
        # Outlook was running HomerView's Open Document. The scripts were
        # reached through MyExtensions, which the factory default.jss chains,
        # so the default chain had to be understood and sometimes rewritten on
        # every machine.
        #
        # Keys in the browser's own key map simply do not exist elsewhere. No
        # guard, no passing the key back, and no guessing what JAWS would have
        # done with it.
        #
        # THE TWO SECTIONS STILL MEAN DIFFERENT THINGS, and both are now inside
        # one file, so both are scoped to the browser:
        #
        #   [Common Keys]  -- any cursor mode in this browser. The nine that
        #                     have to work in the address bar and in forms
        #                     mode: launching, the menu, hotkey help, the
        #                     accessibility scans, the log, diagnostics.
        #   [Virtual Keys] -- only while the virtual cursor is active. The
        #                     thirty-nine that act on a page, several of which
        #                     are plain letters and would type themselves in a
        #                     form field.
        #
        # THE ONE KEY THAT CANNOT LIVE HERE is launching, when the browser is
        # not running or not in front. That is now a Windows shortcut key,
        # Alt+Control+Shift+H, on a desktop shortcut the installer creates. It runs
        # HomerView.exe, which reconnects and raises the window or starts the
        # browser, so it needs no screen reader at all -- which is why one
        # shortcut serves JAWS and NVDA alike.
        $sBrowserBase = [System.IO.Path]::GetFileNameWithoutExtension($sBrowserExe)
        $sConfigBase = browserConfigName $pathUser $pathShared $sBrowserBase
        $pathBrowserJss = Join-Path $pathUser "$sConfigBase.jss"
        $pathBrowserJkm = Join-Path $pathUser "$sConfigBase.jkm"

        # A BROWSER THAT IS NOT THE ONE WE LAST WROTE FOR HAS TO BE CLEARED
        # FIRST. Changing the setting from Edge to Chrome leaves Edge's key map
        # holding thirty-nine keys that answer to scripts Chrome's script file
        # loads, and the reader has two browsers claiming Control+O. The
        # manifest records which browser this folder was done for, so the
        # question can be asked rather than assumed.
        $sPreviousBase = ""
        foreach ($sLine in $lManifest) {
            if ($sLine -match '^browser\|(.+)$') { $sPreviousBase = $Matches[1] }
        }
        if ($sPreviousBase -and $sPreviousBase -ne $sConfigBase) {
            writeLog "  this folder was set up for $sPreviousBase and the browser is now $sConfigBase"
            foreach ($sSuffix in @("jkm", "jss", "jsb")) {
                $pathOld = Join-Path $pathUser "$sPreviousBase.$sSuffix"
                if (-not (Test-Path $pathOld)) { continue }
                if ($lManifest -contains "created|$sPreviousBase.$sSuffix") {
                    Remove-Item $pathOld -Force -ErrorAction SilentlyContinue
                    writeLog "    removed $sPreviousBase.$sSuffix, which we created"
                } elseif ($sSuffix -eq "jkm") {
                    $iOut = removeOurBlock $pathOld
                    writeLog "    took $iOut of our lines back out of $sPreviousBase.jkm"
                }
            }
            $lManifest = @($lManifest | Where-Object { $_ -notlike "*|$sPreviousBase.*" -and $_ -notlike "browser|*" })
        }

        # THE SCRIPT FILE, WHICH LAYERS RATHER THAN REPLACES. The scripting
        # documentation's own word for it: "when one script set is loaded on
        # top of another such that scripts in the set loaded later supersede
        # scripts loaded in an earlier set. Scripts which are not overridden in
        # a set loaded later are INHERITED from a set loaded earlier." So the
        # user file Uses the factory browser binary first, when JAWS ships one,
        # and HomerView.jsb second. Everything Vispero provides still works and
        # ours is added on top.
        #
        # WRITTEN ONLY IF ABSENT, so a file somebody else made is never
        # overwritten.
        $bScriptsOk = $false
        $pathSharedBrowserJsb = ""
        if ($pathShared) {
            $sTry = Join-Path $pathShared "$sConfigBase.jsb"
            if (Test-Path $sTry) { $pathSharedBrowserJsb = $sTry }
        }
        if (-not (Test-Path $pathBrowserJss)) {
            $lJss = @($c_sMarker)
            if ($pathSharedBrowserJsb) {
                $lJss += "Use `"$sConfigBase.jsb`""
                writeLog "    the factory $sConfigBase.jsb will be layered under HomerView's"
            } else {
                writeLog "    JAWS ships no $sConfigBase.jsb, so there is nothing to inherit"
            }
            $lJss += 'Use "HomerView.jsb"'
            $lJss += ""
            $lJss += "; A script file must define something, or it will not compile."
            $lJss += "void function hVBrowserFiller ()"
            $lJss += "return"
            $lJss += "EndFunction"
            Set-Content -Path $pathBrowserJss -Value $lJss -Encoding UTF8
            writeLog "    wrote $sConfigBase.jss, layering HomerView over the browser's own scripts"
            $lManifest += "created|$sConfigBase.jss"
            $bScriptsOk = compileFile $sCompiler $pathBrowserJss
        } else {
            $sExisting = Get-Content $pathBrowserJss -Raw
            if ($sExisting -match '(?im)^\s*use\s+"HomerView\.jsb"') {
                writeLog "    $sConfigBase.jss is already here and already uses HomerView.jsb"
                $bScriptsOk = $true
            } else {
                # SOMEBODY ELSE'S FILE, AND IT STAYS THEIRS. One Use line is
                # added inside our own marked block, which -bUndo takes out
                # again, rather than the file being replaced.
                if (-not (Test-Path "$pathBrowserJss.homerViewBackup")) {
                    Copy-Item $pathBrowserJss "$pathBrowserJss.homerViewBackup" -Force
                    writeLog "    backed up $sConfigBase.jss before adding one line to it"
                }
                $null = removeOurBlock $pathBrowserJss
                $lTheirs = @(Get-Content $pathBrowserJss)
                $iLastUse = -1
                for ($i = 0; $i -lt $lTheirs.Count; $i++) {
                    if ($lTheirs[$i] -match '(?i)^\s*use\s+"') { $iLastUse = $i }
                }
                $lBlock = @($c_sMarker, 'Use "HomerView.jsb"', "$c_sMarker ends")
                if ($iLastUse -lt 0) {
                    $lTheirs = $lBlock + $lTheirs
                } else {
                    $lTheirs = $lTheirs[0..$iLastUse] + $lBlock + $lTheirs[($iLastUse + 1)..($lTheirs.Count - 1)]
                }
                Set-Content -Path $pathBrowserJss -Value $lTheirs -Encoding UTF8
                writeLog "    added Use HomerView.jsb to the $sConfigBase.jss that was already here"
                $lManifest += "edited|$sConfigBase.jss"
                $bScriptsOk = compileFile $sCompiler $pathBrowserJss
            }
        }

        if (-not $bScriptsOk) {
            writeLog "  ERROR: $sConfigBase.jss did not compile, so no key is bound here."
            writeLog "         Binding keys to scripts that cannot load would give silent"
            writeLog "         failures, which is worse than none."
            $iFailed += 1
            writeLog ""
            continue
        }

        # --- the key map ---------------------------------------------------
        #
        # THE COPY IS THE POINT when JAWS ships one. A user key map can be used
        # in place of the factory one rather than alongside it, so a file
        # holding only our keys could cost every binding the factory file
        # provides. Starting from a copy cannot.
        if (-not (Test-Path $pathBrowserJkm)) {
            $sSharedJkm = ""
            if ($pathShared) {
                $sTry = Join-Path $pathShared "$sConfigBase.jkm"
                if (Test-Path $sTry) { $sSharedJkm = $sTry }
            }
            if ($sSharedJkm) {
                Copy-Item $sSharedJkm $pathBrowserJkm -Force
                writeLog "    copied the factory $sConfigBase.jkm into the user folder, so nothing is lost"
            } else {
                Set-Content -Path $pathBrowserJkm -Value @("[Common Keys]", "", "[Virtual Keys]") -Encoding UTF8
                writeLog "    JAWS ships no $sConfigBase.jkm, so a new one was started"
            }
            $lManifest += "created|$sConfigBase.jkm"
        } else {
            if (-not (Test-Path "$pathBrowserJkm.homerViewBackup")) {
                Copy-Item $pathBrowserJkm "$pathBrowserJkm.homerViewBackup" -Force
                writeLog "    backed up $sConfigBase.jkm before changing it"
            }
            # EVERY BLOCK OF OURS COMES OUT ONCE, BEFORE ANY GOES BACK IN.
            # removeOurBlock works on the whole file rather than on one
            # section, and calling it inside the loop below took out the
            # section that had just been written.
            $iOld = removeOurBlock $pathBrowserJkm
            if ($iOld -gt 0) { writeLog "    removed $iOld line(s) written by an earlier release" }
            if ($lManifest -notcontains "created|$sConfigBase.jkm") {
                $lManifest += "edited|$sConfigBase.jkm"
            }
        }

        foreach ($sPair in @(@("[Common Keys]", $lCommonKeys), @("[Virtual Keys]", $lPageKeys))) {
            addToSection $pathBrowserJkm $sPair[0] $sPair[1]
            writeLog "    added $($sPair[1].Count) key(s) to $($sPair[0]) in $sConfigBase.jkm"
        }
        writeLog "      these work only while the browser has focus, and nowhere else"
        $lManifest += "browser|$sConfigBase"

        # What is in the file now, not what was written to it.
        #
        # Every step in this script once reported success while the launch key
        # was being deleted by the next step. A count of lines added is a
        # record of an action; reading the key back is a record of an outcome,
        # and only one of those is worth logging.
        $lAllKeys = $lCommonKeys + $lPageKeys
        $iMissing = 0
        if (Test-Path $pathBrowserJkm) {
            $sFinal = Get-Content $pathBrowserJkm -Raw
            foreach ($sKey in $lAllKeys) {
                if (-not $sFinal.Contains($sKey)) {
                    writeLog "    ERROR: $sKey is not in $sConfigBase.jkm after writing it"
                    $iMissing += 1
                }
            }
        } else {
            writeLog "    ERROR: $sConfigBase.jkm is not there at all after writing it"
            $iMissing += 1
        }

        # AND THE OTHER HALF OF THE PROMISE, CHECKED RATHER THAN ASSERTED.
        # Nothing of ours should be in the default key map, including anything
        # an older release put there. Saying so in the log every run is what
        # keeps the claim honest.
        $pathDefaultJkm = Join-Path $pathUser "default.jkm"
        if (Test-Path $pathDefaultJkm) {
            $sDefault = Get-Content $pathDefaultJkm -Raw
            $iOurs = 0
            foreach ($sKey in $lAllKeys) {
                $sScript = ($sKey -split "=")[1]
                if ($sDefault -match [regex]::Escape($sScript)) { $iOurs += 1 }
            }
            if ($iOurs -gt 0) {
                writeLog "    NOTE: the user default.jkm still names $iOurs HomerView script(s),"
                writeLog "          left by a release before this one. Run -bUndo with that"
                writeLog "          release, or remove those lines by hand."
            } else {
                writeLog "    the user default.jkm names nothing of HomerView's, as intended"
            }
        } else {
            writeLog "    there is no user default.jkm here, which is how HomerView leaves it"
        }

        if ($iMissing -gt 0) {
            $iFailed += 1
        } else {
            writeLog "    all $($lAllKeys.Count) keys read back correctly from $sConfigBase.jkm"
            $iDone += 1
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
    writeLog "RESTART JAWS. Then press Alt+Control+Shift+H, which is a Windows shortcut"
    writeLog "key on the HomerView desktop icon and works whatever has focus."
    writeLog "Every other key works while the browser is in front: Alt+F10"
    writeLog "for the menu, Alt+Shift+H for every key."
    writeLog "With HomerView's browser focused, Insert+Q says which scripts are loaded."
    writeLog "Nothing outside the browser was changed: no default.jss, no default.jkm,"
    writeLog "no MyExtensions. To put back what was written: chainJawsScripts -bUndo"
}
exit 0
