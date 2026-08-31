# buildHomerViewBridge.ps1 -- compile HomerViewBridge.exe
#
# The bridge is the one piece JAWS scripting cannot supply for itself: the
# WebSocket half of the Chrome DevTools Protocol. Everything else the JAWS
# scripts do themselves.
#
# It builds with csc.exe from the .NET Framework, which is on every Windows 10
# and 11 machine already, so this needs no Visual Studio, no NuGet and no
# download.
#
# A detailed log is written beside this script, whatever happens. Upload that
# rather than the console output: a redirect catches only what was printed,
# while the log also records the environment, every command run and its exit
# code, which is usually where the answer is.

$ErrorActionPreference = "Stop"

$pathRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pathLog = Join-Path $pathRoot "buildHomerViewBridge.log"

function writeLog {
    param([string] $sMessage)
    $sStamped = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $sMessage
    Write-Host $sStamped
    try { Add-Content -Path $pathLog -Value $sStamped -Encoding UTF8 } catch { }
}

Set-Content -Path $pathLog -Value "" -Encoding UTF8
writeLog "buildHomerViewBridge starting"
writeLog "  script:            $($MyInvocation.MyCommand.Path)"
writeLog "  PowerShell:        $($PSVersionTable.PSVersion)"
writeLog "  platform:          $([System.Environment]::OSVersion.VersionString)"
writeLog "  64 bit process:    $([System.Environment]::Is64BitProcess)"
writeLog "  working directory: $(Get-Location)"
writeLog "  project root:      $pathRoot"
writeLog "  command line:      $($MyInvocation.Line.Trim())"
writeLog ""

# The source must be here before anything else is attempted.
$pathSource = Join-Path $pathRoot "HomerViewBridge.cs"
if (-not (Test-Path $pathSource)) {
    writeLog "ERROR: HomerViewBridge.cs is not in $pathRoot."
    writeLog "       Run this from the folder holding the bridge source."
    exit 1
}
writeLog "Source: $pathSource ($((Get-Item $pathSource).Length) bytes)"

# The compiler. 64 bit only, as asked, so the bridge matches a 64 bit JAWS.
$pathCompiler = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
writeLog "Looking for the compiler at $pathCompiler"
if (-not (Test-Path $pathCompiler)) {
    writeLog "ERROR: the .NET Framework compiler was not found."
    writeLog "       That file ships with Windows, so something is unusual here."
    writeLog "       These are the framework versions present:"
    foreach ($folder in (Get-ChildItem (Join-Path $env:WINDIR "Microsoft.NET\Framework64") `
            -Directory -ErrorAction SilentlyContinue)) {
        writeLog "         $($folder.Name)"
    }
    exit 1
}
writeLog "Compiler found."

$pathOutput = Join-Path $pathRoot "HomerViewBridge.exe"
if (Test-Path $pathOutput) {
    Remove-Item $pathOutput -Force
    writeLog "Removed the previous $pathOutput"
}

# winexe rather than exe, so the desktop shortcut that carries Alt+Control+H
# does not put a console window on the screen. Every answer is written to a
# file, so nothing is lost by having no console.
$lArguments = @("/nologo", "/target:winexe", "/platform:x64",
    "/out:$pathOutput", $pathSource)
writeLog "Running: csc.exe $($lArguments -join ' ')"
$sOutput = & $pathCompiler @lArguments 2>&1 | Out-String
$iExit = $LASTEXITCODE
writeLog "csc.exe exit code $iExit"

# Every line the compiler said, whether it succeeded or not. A warning on a
# build that worked is often what explains a failure on the next one.
foreach ($sLine in ($sOutput -split "`n")) {
    if ($sLine.Trim()) { writeLog "    $($sLine.Trim())" }
}

if ($iExit -ne 0 -or -not (Test-Path $pathOutput)) {
    writeLog ""
    writeLog "ERROR: the bridge was not built."
    exit 1
}

$nSize = [math]::Round((Get-Item $pathOutput).Length / 1KB)
writeLog "Built $pathOutput, $nSize KB."

# It must at least start. A program that compiles and will not run is worth
# finding out about here rather than from a JAWS script that got no answer.
writeLog ""
writeLog "Checking that it runs."
$pathProbe = Join-Path $env:TEMP "HomerViewBridgeProbe.txt"
if (Test-Path $pathProbe) { Remove-Item $pathProbe -Force }
& $pathOutput "tabs" $pathProbe 2>&1 | ForEach-Object {
    if ("$_".Trim()) { writeLog "    $_" }
}
writeLog "Exit code $LASTEXITCODE"
if (Test-Path $pathProbe) {
    $sProbe = (Get-Content $pathProbe -Raw)
    writeLog "It wrote $((Get-Item $pathProbe).Length) bytes."
    writeLog "    $($sProbe.Substring(0, [math]::Min(300, $sProbe.Length)))"
    if ($sProbe -match '"error"') {
        writeLog ""
        writeLog "That error is expected when HomerView's browser is not running."
        writeLog "It means the bridge itself works: it ran, tried, and reported."
    }
    Remove-Item $pathProbe -Force
} else {
    writeLog "WARNING: it produced no file, which it should do even on failure."
}

writeLog ""
writeLog "Ready. The JAWS scripts can now call HomerViewBridge.exe."
writeLog "The log is at $pathLog"
