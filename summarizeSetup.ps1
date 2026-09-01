# Shows the Results box after Setup has finished.
#
# WHY THIS IS A SEPARATE PROGRAM. The finish page's checkboxes run AFTER the
# installer's own code has had its last say, so the disposition of each one is
# not known until Setup is on its way out. Inno launches this without waiting,
# so the box appears once everything is done and closing it is the last thing
# that happens.
#
# It reads what the installer already wrote, adds what only this moment can
# know, and says it once.
param([string] $pathFolder = "")

$ErrorActionPreference = "Continue"
if (-not $pathFolder) { $pathFolder = Join-Path $env:LOCALAPPDATA "HomerView\logs" }
$pathResults = Join-Path $pathFolder "HomerView_setup_results.txt"
$pathLog = Join-Path $pathFolder "HomerView_setup.log"

$sMessage = ""
if (Test-Path $pathResults) {
    $sMessage = (Get-Content $pathResults -Raw)
} else {
    $sMessage = "HomerView is installed."
}

# WHAT ONLY THIS MOMENT KNOWS: the finish-page steps have now run, so their
# outcome can be read off the disk rather than guessed at.
$sBreak = [Environment]::NewLine

# THE JAWS OUTCOME COMES FROM THE JAWS LOG, which is the only place it is
# recorded now. That script ends with a line of the form
#   Finished. 3 settings folders done, 0 skipped, 0 with a problem.
# so the newest log in this folder answers the question without a second file
# in C:\temp saying the same thing and falling out of step with it.
$oNewest = Get-ChildItem -Path $pathFolder -Filter "HomerViewJAWS*.log" -File `
    -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if ($oNewest) {
    $sFinished = (Select-String -Path $oNewest.FullName -Pattern "Finished\. .*settings folders" |
        Select-Object -Last 1).Line
    if ($sFinished -match "(\d+) settings folders done, (\d+) skipped, (\d+) with a problem") {
        $iDone = [int] $Matches[1]
        $iTrouble = [int] $Matches[3]
        if ($iTrouble -gt 0) {
            $sMessage += "  JAWS scripts: FAILED in $iTrouble folder(s). The log named below says why." + $sBreak
        } elseif ($iDone -gt 0) {
            $sWord = if ($iDone -eq 1) { "folder" } else { "folders" }
            $sMessage += "  JAWS scripts: installed for $iDone JAWS $sWord." + $sBreak
        } else {
            $sMessage += "  JAWS scripts: no JAWS version was set up." + $sBreak
        }
    }
}

$pathAddon = Join-Path $env:APPDATA "nvda\addons"
if ((Test-Path (Join-Path $pathAddon "homerView")) -or
    (Test-Path (Join-Path $pathAddon "homerView.pendingInstall"))) {
    $sMessage += "  NVDA add-on: installed. Restart NVDA to use it." + $sBreak
}

$sMessage += $sBreak + "The full log is:" + $sBreak + "  " + $pathLog + $sBreak
# THE LAST THING THE READER HEARS, so it has to be the key that actually
# works. It said Alt+JAWS+H and Alt+NVDA+H until 31 August 2026, which were
# right while HomerView bound a key in every application. It no longer does:
# every screen reader key is now scoped to the browser, and starting the
# browser from anywhere else is a Windows shortcut key on the desktop icon.
#
# Worth noticing that nothing failed here. The installer was correct, the
# keys were correct, and the one sentence a first-time user reads was wrong.
# A message is as much a part of the product as the code it describes.
$sMessage += $sBreak + "To start HomerView, press Alt+Control+Shift+H. That is a Windows" + $sBreak
$sMessage += "shortcut key on the HomerView icon on your desktop, so it works" + $sBreak
$sMessage += "whichever screen reader you use." + $sBreak
$sMessage += $sBreak + "Every other HomerView key works while that browser window is in" + $sBreak
$sMessage += "front, and does nothing in any other program." + $sBreak
$sMessage += $sBreak + "In JAWS, restart JAWS first." + $sBreak

Add-Type -AssemblyName System.Windows.Forms | Out-Null
[System.Windows.Forms.MessageBox]::Show($sMessage, "HomerView Setup Results",
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null
