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

# ONLY WHAT WAS TICKED (29 September 2026). The installer wrote the ticked
# captions to HomerView_ticked.txt when Finish was pressed; each screen reader
# is reported only when its box was among them, and nothing else is added but
# where the logs are.
$pathTicked = Join-Path $pathFolder "HomerView_ticked.txt"
$sTicked = ""
if (Test-Path -LiteralPath $pathTicked) {
    $sTicked = (Get-Content -LiteralPath $pathTicked -ErrorAction SilentlyContinue) -join "`n"
    try { Remove-Item -LiteralPath $pathTicked -Force } catch { }
}
$sMessage = $sMessage.TrimEnd() + $sBreak

# The JAWS outcome comes from the JAWS log, which ends with a line of the form
#   Finished. 3 settings folders done, 0 skipped, 0 with a problem.
if ($sTicked -match "JAWS") {
    $oNewest = Get-ChildItem -Path $pathFolder -Filter "HomerViewJAWS*.log" -File `
        -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    $sLine = "  JAWS scripts: the step left no record. The log says why."
    if ($oNewest) {
        $sFinished = (Select-String -Path $oNewest.FullName -Pattern "Finished\. .*settings folders" |
            Select-Object -Last 1).Line
        if ($sFinished -match "(\d+) settings folders done, (\d+) skipped, (\d+) with a problem") {
            $iDone = [int] $Matches[1]
            $iTrouble = [int] $Matches[3]
            if ($iTrouble -gt 0) {
                $sLine = "  JAWS scripts: NOT installed -- they did not compile for $iTrouble JAWS version(s), so nothing was left behind. The log has the compiler's words."
            } elseif ($iDone -gt 0) {
                $sWord = if ($iDone -eq 1) { "version" } else { "versions" }
                $sLine = "  JAWS scripts: installed and compiled for $iDone JAWS $sWord."
            }
        }
    }
    $sMessage += $sLine + $sBreak
}

if ($sTicked -match "NVDA") {
    $pathAddon = Join-Path $env:APPDATA "nvda\addons"
    $bRunning = [bool](Get-Process -Name nvda -ErrorAction SilentlyContinue)
    if ((Test-Path (Join-Path $pathAddon "homerView")) -or (Test-Path (Join-Path $pathAddon "homerView.pendingInstall"))) {
        if ($bRunning) { $sMessage += "  NVDA add-on: installed. Restart NVDA to use it." + $sBreak }
        else { $sMessage += "  NVDA add-on: installed. NVDA loads it when it next starts." + $sBreak }
    } else {
        $sMessage += "  NVDA add-on: NOT installed. The log says why." + $sBreak
    }
    # For the log: what NVDA now has, and what its own log says.
    try {
        $sCheck = Join-Path $PSScriptRoot "installJawsScripts.cmd"
        & cmd.exe /c "`"$sCheck`" -sState nvda -bQuiet" | Out-Null
    } catch { }
}

$sMessage += $sBreak + "Logs are kept in $pathFolder." + $sBreak

# At most one blank line in a row.
$lsShown = @()
foreach ($sLine in ($sMessage -split "\r?\n")) {
    if ($sLine.Trim() -eq "" -and ($lsShown.Count -eq 0 -or $lsShown[-1].Trim() -eq "")) { continue }
    $lsShown += $sLine
}
$sMessage = ($lsShown -join $sBreak).TrimEnd()

Add-Type -AssemblyName System.Windows.Forms | Out-Null
[System.Windows.Forms.MessageBox]::Show($sMessage, "HomerView Setup Results",
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null
