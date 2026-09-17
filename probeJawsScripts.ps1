# probeJawsScripts.ps1 -- what JAWS actually has, and where.
#
# WHY THIS EXISTS. Control+F in Edge answers "Unknown script call to virtual
# find" and the same key works in Chrome. Two explanations have been offered
# for that and both were wrong, so this one gathers the facts instead of
# proposing a third.
#
# WHAT IS KNOWN. HomerView writes a user msedge.jss, msedge.jkm and msedge.jsb
# and writes nothing for Chrome. Edge is broken and Chrome is not. So the fault
# is in what those three files do to JAWS's own arrangements.
#
# WHAT IS NOT KNOWN, and each of these decides the fix:
#
#   1. WHICH KEY MAP SUPPLIES Control+F, and which script name it gives. That
#      is the whole question. "Unknown script call" means a key map named a
#      script that is not loaded, so finding the key map and the name says what
#      has to be loaded.
#   2. WHERE THE FACTORY SETTINGS ARE. Every run so far has reported "JAWS
#      ships no msedge.jsb", having looked in ProgramData and Program Files. If
#      the factory files are somewhere else, that report has been meaningless
#      and the layering it decides has never happened.
#   3. WHETHER JAWS SHIPS AN EDGE SCRIPT SET AT ALL. If it does, HomerView's
#      user msedge.jss replaces it, and everything that set provides is gone.
#      If it does not, the fault is in how a lone application script set
#      interacts with the default one.
#
# It reads. It changes nothing, creates nothing, and deletes nothing.
#
# Writes probeJawsScripts.log beside this script.

param(
    [string] $pathLogFile = ""
)

$ErrorActionPreference = "Continue"
$pathRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $pathLogFile) { $pathLogFile = Join-Path $pathRoot "probeJawsScripts.log" }
$script:lReport = @()

function writeLog {
    param([string] $sMessage = "")
    $sLine = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $sMessage"
    Write-Host $sMessage
    $script:lReport += $sLine
}

function saveLog {
    try {
        Set-Content -Path $pathLogFile -Value $script:lReport -Encoding UTF8
        Write-Host "The log is at $pathLogFile"
    } catch {
        Write-Host "The log could not be written: $($_.Exception.Message)"
    }
}

writeLog "probeJawsScripts"
writeLog "  script:            $($MyInvocation.MyCommand.Path)"
writeLog "  PowerShell:        $($PSVersionTable.PSVersion)"
writeLog "  working directory: $(Get-Location)"
writeLog "  command line:      $($MyInvocation.Line.Trim())"
writeLog "  It only reads. Nothing is changed, created or deleted."
writeLog ""

# --- Every folder JAWS might keep settings in --------------------------------
$lVersions = @()
try {
    $lVersions = @(Get-ChildItem -Path (Join-Path $env:APPDATA "Freedom Scientific\JAWS") `
        -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
} catch {
}
if (-not $lVersions) { writeLog "No JAWS versions found under the user profile." }
writeLog "JAWS versions: $($lVersions -join ', ')"
writeLog ""

foreach ($sVersion in $lVersions) {
    writeLog "================================================================"
    writeLog "JAWS $sVersion"
    writeLog "================================================================"

    $sTarget = ""
    try {
        $sTarget = (Get-ItemProperty -Path "HKLM:\Software\Freedom Scientific\JAWS\$sVersion" `
            -Name "Target" -ErrorAction Stop).Target
    } catch {
    }
    writeLog "  registry Target: $(if ($sTarget) { $sTarget } else { '(could not be read)' })"

    # Every folder worth looking in, whether or not it exists. Reporting the
    # ones that do NOT exist matters as much: that is how the wrong shared
    # folder went unnoticed for so long.
    $lFolders = @()
    foreach ($sLanguage in @("enu", "")) {
        if ($sTarget) {
            $lFolders += (Join-Path $sTarget "Settings\$sLanguage")
        }
        $lFolders += (Join-Path $env:APPDATA "Freedom Scientific\JAWS\$sVersion\Settings\$sLanguage")
        $lFolders += (Join-Path $env:ProgramData "Freedom Scientific\JAWS\$sVersion\Settings\$sLanguage")
        $lFolders += (Join-Path ${env:ProgramFiles} "Freedom Scientific\JAWS\$sVersion\Settings\$sLanguage")
        $lFolders += (Join-Path ${env:ProgramFiles(x86)} "Freedom Scientific\JAWS\$sVersion\Settings\$sLanguage")
    }
    $lFolders = @($lFolders | Where-Object { $_ } | Select-Object -Unique)

    foreach ($sFolder in $lFolders) {
        if (-not (Test-Path $sFolder)) {
            writeLog "  MISSING  $sFolder"
            continue
        }
        writeLog ""
        writeLog "  FOLDER   $sFolder"
        # Only the files that decide anything, or the log is unreadable.
        $lInteresting = @(Get-ChildItem -Path $sFolder -File -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Name -match '(?i)^(default|msedge|chrome|brave|vivaldi|MyExtensions|HomerView|ConfigNames)\.' -or
                $_.Name -match '(?i)^(msedge|chrome)\..*homerViewHeld$'
            })
        if (-not $lInteresting) {
            writeLog "    nothing of interest here"
            continue
        }
        foreach ($oFile in ($lInteresting | Sort-Object Name)) {
            writeLog ("    {0,-34} {1,9} bytes  {2}" -f $oFile.Name, $oFile.Length,
                $oFile.LastWriteTime.ToString("yyyy-MM-dd HH:mm"))
        }

        # --- THE QUESTION THIS PROBE EXISTS FOR ---------------------------
        #
        # Which key map here binds Control+F, and to what script name. An
        # "Unknown script call" means a key map named a script that is not
        # loaded, so this line identifies both halves of the problem at once.
        foreach ($oMap in ($lInteresting | Where-Object { $_.Name -match '(?i)\.jkm$' })) {
            $sSection = ""
            $iLine = 0
            foreach ($sLine in (Get-Content $oMap.FullName -ErrorAction SilentlyContinue)) {
                $iLine += 1
                $sTrimmed = $sLine.Trim()
                if ($sTrimmed -match '^\[(.+)\]$') { $sSection = $Matches[1]; continue }
                if ($sTrimmed -match '(?i)^(Control\+F|Control\+Shift\+F|F3|Control\+Home|Control\+End)\s*=') {
                    writeLog "      KEY  $($oMap.Name) [$sSection] line $iLine : $sTrimmed"
                }
            }
        }

        # And what our own browser script file says, since that is the file
        # under suspicion and it is three lines long.
        foreach ($oScript in ($lInteresting | Where-Object { $_.Name -match '(?i)^(msedge|chrome)\.jss$' })) {
            writeLog "      CONTENTS of $($oScript.Name):"
            foreach ($sLine in (Get-Content $oScript.FullName -ErrorAction SilentlyContinue)) {
                writeLog "        $sLine"
            }
        }
    }
    writeLog ""
}

writeLog "================================================================"
writeLog "WHAT TO DO WITH THIS"
writeLog "================================================================"
writeLog "Send probeJawsScripts.log back. The lines beginning KEY say which key"
writeLog "map binds Control+F and which script it names. The FOLDER lines say"
writeLog "where the factory files really are, which every run so far has been"
writeLog "guessing at."
writeLog ""
writeLog "Nothing was changed by this script."
saveLog
exit 0
